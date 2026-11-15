"""Run approved jobs locally while keeping program output out of the chat/tool return path.

Only fixed job names are accepted. Child stdout/stderr go directly to ignored local logs;
the parent emits a small, validated status object and never includes exception text or paths.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid


ROOT = Path(__file__).resolve().parents[1]
PRIVATE_DIR = ROOT / "artifacts_private" / "runs"
JOBS = {
    "runner_self_test": "runner_self_test",
    "target_smoke": "target_smoke",
    "target_infer": "target_infer",
    "target_validate": "target_validate",
    "reproduce": "reproduce",
}
CHECKS = {
    "frame_contract", "finite_evidence", "csv_contract", "byte_reproduction",
    "offline_guard", "inputs_present",
}
STATES = {"pass", "fail", "skip"}
FAILURE_CODES = {
    "INPUT_MISSING",
    "INPUT_INVALID",
    "DEPENDENCY_MISSING",
    "RESOURCE_LIMIT",
    "INTERNAL_ERROR",
}


def _status(job: str, state: str, checks: dict[str, str] | None = None,
            failure_code: str | None = None) -> dict[str, object]:
    result: dict[str, object] = {
        "job": job,
        "status": state,
        "checks": checks or {},
        "details": "retained_locally",
    }
    if failure_code:
        result["failure_code"] = failure_code
    return result


def _private_root() -> Path:
    root = ROOT.resolve()
    private = PRIVATE_DIR.resolve()
    if root not in private.parents:
        raise RuntimeError("private output path must stay inside the solution repository")
    private.mkdir(parents=True, exist_ok=True)
    return private


def _read_worker_status(path: Path, job: str) -> dict[str, object]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return _status(job, "failed", failure_code="INTERNAL_ERROR")

    if not isinstance(data, dict) or data.get("job") != job:
        return _status(job, "failed", failure_code="INTERNAL_ERROR")
    state = data.get("status")
    if not isinstance(state, str) or state not in {"completed", "failed"}:
        return _status(job, "failed", failure_code="INTERNAL_ERROR")
    raw_checks = data.get("checks", {})
    if not isinstance(raw_checks, dict):
        return _status(job, "failed", failure_code="INTERNAL_ERROR")
    checks: dict[str, str] = {}
    for key, value in raw_checks.items():
        if not isinstance(key, str) or key not in CHECKS:
            return _status(job, "failed", failure_code="INTERNAL_ERROR")
        if not isinstance(value, str) or value not in STATES:
            return _status(job, "failed", failure_code="INTERNAL_ERROR")
        checks[key] = value
    failure = data.get("failure_code")
    if failure is not None and (not isinstance(failure, str) or failure not in FAILURE_CODES):
        return _status(job, "failed", failure_code="INTERNAL_ERROR")
    return _status(job, state, checks, failure)


def _launch(job: str, command: list[str], status_path: Path, log_path: Path,
            timeout_seconds: int) -> dict[str, object]:
    # Allow only runtime/path variables needed by CPython and the local competition bundle.
    # Deliberately exclude inherited credentials, arbitrary PYTHONPATH, and model-provider keys.
    env = {key: os.environ[key] for key in (
        "PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "USERPROFILE",
        "APPDATA", "LOCALAPPDATA", "HOMEDRIVE", "HOMEPATH", "PATHEXT",
        "MTAH_DATA_DIR",
    ) if key in os.environ}
    env.update({
        "HF_HUB_OFFLINE": "1",
        "HF_HUB_DISABLE_TELEMETRY": "1",
        "TRANSFORMERS_OFFLINE": "1",
        "DO_NOT_TRACK": "1",
        "PYTHONNOUSERSITE": "1",
        "PYTHONHASHSEED": "0",
        "CUDA_VISIBLE_DEVICES": "",
        "OMP_NUM_THREADS": "1",
        "OPENBLAS_NUM_THREADS": "1",
        "MKL_NUM_THREADS": "1",
        "NUMEXPR_MAX_THREADS": "1",
    })
    try:
        with log_path.open("wb") as logfile:
            completed = subprocess.run(
                command,
                cwd=ROOT,
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=logfile,
                stderr=subprocess.STDOUT,
                timeout=timeout_seconds,
                check=False,
                shell=False,
            )
    except subprocess.TimeoutExpired:
        return _status(job, "failed", failure_code="RESOURCE_LIMIT")
    except OSError:
        return _status(job, "failed", failure_code="INTERNAL_ERROR")

    result = _read_worker_status(status_path, job)
    if completed.returncode != 0 and result["status"] == "completed":
        return _status(job, "failed", failure_code="INTERNAL_ERROR")
    return result


def run(job: str, timeout_seconds: int = 21600) -> dict[str, object]:
    if job not in JOBS:
        raise ValueError("unsupported job")
    if not 1 <= timeout_seconds <= 21600:
        raise ValueError("timeout outside the supported range")

    private = _private_root()
    run_id = uuid.uuid4().hex
    status_path = private / f"{run_id}.status.json"
    log_path = private / f"{run_id}.log"
    status_path.unlink(missing_ok=True)

    # The environment is allowlisted, and -s suppresses user site packages while preserving the
    # explicit PYTHONHASHSEED. The bootstrap adds this repository, blocks Python socket access,
    # marks the guarded launch, and imports the private worker.
    bootstrap = (
        "import os, runpy, socket, sys; "
        "root=sys.argv[1]; sys.path.insert(0, root); "
        "blocked=lambda *a, **k: (_ for _ in ()).throw(OSError('network disabled')); "
        "socket.socket=blocked; socket.create_connection=blocked; socket.getaddrinfo=blocked; "
        "os.environ['MALWAROUS_SAFE_RUNNER']='1'; "
        "sys.argv=['malwarous.private_worker', sys.argv[2], sys.argv[3]]; "
        "runpy.run_module('malwarous.private_worker', run_name='__main__')"
    )
    command = [sys.executable, "-s", "-c", bootstrap, str(ROOT), JOBS[job], str(status_path)]
    return _launch(job, command, status_path, log_path, timeout_seconds)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a fixed local job with status-only output")
    parser.add_argument("job", choices=tuple(JOBS))
    parser.add_argument("--timeout", type=int, default=21600)
    args = parser.parse_args()
    try:
        result = run(args.job, args.timeout)
    except Exception:
        result = _status(args.job, "failed", failure_code="INTERNAL_ERROR")
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0 if result["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())

