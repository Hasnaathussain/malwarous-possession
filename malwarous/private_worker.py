"""Private child process entry point. Never prints; all diagnostics stay in the local log."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import socket
import sys
import traceback


ALLOWED_JOBS = {"runner_self_test", "target_smoke", "target_infer", "target_validate", "reproduce"}
ALLOWED_CHECKS = {
    "frame_contract", "finite_evidence", "csv_contract", "byte_reproduction",
    "offline_guard", "inputs_present",
}
ALLOWED_STATES = {"pass", "fail", "skip"}
FAILURE_TYPES = {
    "FileNotFoundError": "INPUT_MISSING",
    "OSError": "INPUT_INVALID",
    "PermissionError": "INPUT_INVALID",
    "ValueError": "INPUT_INVALID",
    "ImportError": "DEPENDENCY_MISSING",
    "ModuleNotFoundError": "DEPENDENCY_MISSING",
    "MemoryError": "RESOURCE_LIMIT",
    "TimeoutError": "RESOURCE_LIMIT",
}

ROOT = Path(__file__).resolve().parents[1]
PRIVATE_OUTPUT = ROOT / "artifacts_private" / "Malwarous.csv"
REPRODUCTION_OUTPUT = ROOT / "artifacts_private" / ".reproduction-check.csv"
EXPECTED_FRAMES = 199_319
LOCK_ID = "malwarous-phase1-v1"
SELECTION_COMMIT = "4fafcab63ad1bee328cea10469cdff1abbb51070"
SELECTION_CODE_FINGERPRINT_RAW = "71600506d32a7aa96b0c5056345433f4cf28a80c8c73ce70df50437d6aa7627f"
PROTOCOL_SHA256 = "7d04b40943e62d6870a1280bb06daf3e4215bba26fe3c5af75a5349e15ebe7d4"
SELECTION_CODE_FINGERPRINT_LF = "5bcd5fc3ef4cdb5b2ae80ff5e8f1bbfb796354680606e5482034ae8cbb63958e"
GAMES_PY_SHA256 = "3b2122794e9e0476e2b3a871d14880e5fa47c4feaeacf99caef054c2309076ce"

# Must match scripts/run_external_experiments.py:CODE_INPUTS. This is the exact public-code
# fingerprint that was evaluated before the release lock; it includes the organizer baseline.
SELECTION_CODE_INPUTS = (
    "scripts/run_external_experiments.py",
    "scripts/compute_external_selection.py",
    "scripts/fetch_sportec.py",
    "malwarous/experiments.py",
    "malwarous/external_pipeline.py",
    "malwarous/external_sportec.py",
    "malwarous/features.py",
    "malwarous/models.py",
    "malwarous/corruption.py",
    "malwarous/temporal.py",
    "evaluation/possession_metrics.py",
    "starter/baseline.py",
    "requirements.in",
    "requirements.lock",
    "requirements-starter.txt",
)
RELEASE_RUNNER_INPUTS = (
    "configs/experiment_protocol.json",
    "games.py",
    "starter/baseline.py",
    "evaluation/possession_metrics.py",
    "malwarous/__init__.py",
    "malwarous/features.py",
    "malwarous/inference.py",
    "malwarous/metrica_ingest.py",
    "malwarous/models.py",
    "malwarous/private_worker.py",
    "malwarous/safe_runner.py",
    "malwarous/temporal.py",
    "requirements.in",
    "requirements.lock",
    "requirements-starter.txt",
)


def _write_status(path: Path, job: str, state: str, checks: dict[str, str],
                  failure_code: str | None = None) -> None:
    safe_checks = {
        key: value for key, value in checks.items()
        if key in ALLOWED_CHECKS and value in ALLOWED_STATES
    }
    status = {"job": job, "status": state, "checks": safe_checks}
    if failure_code:
        status["failure_code"] = failure_code
    path.write_text(json.dumps(status, sort_keys=True), encoding="utf-8")


def _offline_guard_passes() -> bool:
    try:
        socket.socket()
    except OSError:
        return True
    return False


def _locked_window() -> int:
    """Read and enforce the committed release lock; never derive policy from target data."""
    path = ROOT / "configs" / "final_candidate.json"
    lock = json.loads(path.read_text(encoding="utf-8"))
    if (lock.get("lock_id") != LOCK_ID
            or lock.get("candidate") != "nearest_smooth50_reference"
            or lock.get("mode") != "reference"
            or lock.get("code_commit") != SELECTION_COMMIT
            or lock.get("code_fingerprint") != SELECTION_CODE_FINGERPRINT_RAW
            or lock.get("protocol_sha256") != PROTOCOL_SHA256
            or lock.get("reference_window") != 50):
        raise ValueError("release lock does not match the approved candidate")
    protocol_path = ROOT / "configs" / "experiment_protocol.json"
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    canonical_protocol = json.dumps(
        protocol, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")
    if hashlib.sha256(canonical_protocol).hexdigest() != PROTOCOL_SHA256:
        raise ValueError("experiment protocol no longer matches the release lock")
    digest_raw = hashlib.sha256()
    digest_lf = hashlib.sha256()
    for relative in SELECTION_CODE_INPUTS:
        encoded_name = relative.encode("utf-8")
        content = (ROOT / relative).read_bytes()
        for digest, source in ((digest_raw, content),
                               (digest_lf, content.replace(b"\r\n", b"\n"))):
            digest.update(len(encoded_name).to_bytes(4, "big"))
            digest.update(encoded_name)
            digest.update(len(source).to_bytes(8, "big"))
            digest.update(source)
    if (digest_raw.hexdigest() != SELECTION_CODE_FINGERPRINT_RAW
            and digest_lf.hexdigest() != SELECTION_CODE_FINGERPRINT_LF):
        raise ValueError("selection code no longer matches the frozen release lock")
    games_source = (ROOT / "games.py").read_bytes().replace(b"\r\n", b"\n")
    if hashlib.sha256(games_source).hexdigest() != GAMES_PY_SHA256:
        raise ValueError("official game constants no longer match the frozen reference")

    runner_lock_path = ROOT / "configs" / "target_runner_lock.json"
    runner_lock_bytes = runner_lock_path.read_bytes().replace(b"\r\n", b"\n")
    if hashlib.sha256(runner_lock_bytes).hexdigest() != lock.get("target_runner_lock_sha256"):
        raise ValueError("target runner lock does not match the release configuration")
    runner_lock = json.loads(runner_lock_bytes.decode("utf-8"))
    if (runner_lock.get("schema") != 1
            or runner_lock.get("selection_lock_id") != LOCK_ID
            or runner_lock.get("candidate") != lock.get("candidate")
            or runner_lock.get("mode") != lock.get("mode")
            or runner_lock.get("reference_window") != 50
            or runner_lock.get("selection_commit") != SELECTION_COMMIT
            or runner_lock.get("selection_code_fingerprint") != lock.get("code_fingerprint")
            or runner_lock.get("selection_protocol_sha256") != lock.get("protocol_sha256")):
        raise ValueError("target runner lock does not describe the selected candidate")
    locked_inputs = runner_lock.get("inputs")
    if not isinstance(locked_inputs, dict) or set(locked_inputs) != set(RELEASE_RUNNER_INPUTS):
        raise ValueError("target runner lock has an unexpected input set")
    for relative in RELEASE_RUNNER_INPUTS:
        content = (ROOT / relative).read_bytes().replace(b"\r\n", b"\n")
        if hashlib.sha256(content).hexdigest() != locked_inputs.get(relative):
            raise ValueError("target inference source no longer matches the release lock")
    return 50


def _require_target_assets() -> None:
    """Check only that the official starter inputs exist; this does not open their contents."""
    from games import GAME, require

    require(["atd_meta", "atd_raw"], game=GAME)


def _generate_locked_submission(output_path: Path) -> None:
    """Generate the fixed reference candidate. All source parsing remains inside this process."""
    window = _locked_window()

    import numpy as np

    from games import GAME, source_frames
    from malwarous.inference import write_submission
    from starter.baseline import build, smooth

    n_expected = source_frames("tactical", GAME)
    if n_expected != EXPECTED_FRAMES:
        raise ValueError("official frame contract changed")

    # These are the organizer's published nearest-player labels and smoothing implementation.
    # Their progress output and any parser diagnostics remain in the private child log.
    codes = np.asarray(build(game=GAME), dtype=np.int8)
    if codes.shape != (n_expected,) or not np.isin(codes, (-1, 0, 1)).all():
        raise ValueError("reference output violates the frame contract")

    labels = np.asarray(smooth(codes, window), dtype="<U1")
    if labels.shape != (n_expected,) or not np.isin(labels, ("H", "A", "D")).all():
        raise ValueError("reference labels violate the class contract")

    code_map = {"H": 0, "A": 1, "D": 2}
    numeric = np.fromiter((code_map[str(label)] for label in labels), dtype=np.int8,
                          count=n_expected)
    write_submission(output_path, numeric, n_expected=n_expected)


def _validate_submission(path: Path) -> bool:
    """Use the organizer validator and require the exact two-column file contract."""
    _locked_window()

    import csv

    from games import GAME, source_frames
    from malwarous.inference import official_csv_valid

    if not path.is_file() or source_frames("tactical", GAME) != EXPECTED_FRAMES:
        return False
    try:
        with path.open("r", encoding="ascii", newline="") as stream:
            header = next(csv.reader(stream), None)
    except (OSError, UnicodeError, csv.Error):
        return False
    return (header == ["frame", "label"]
            and official_csv_valid(path, n_expected=EXPECTED_FRAMES))


def execute(job: str) -> dict[str, str]:
    if job == "runner_self_test":
        if _offline_guard_passes():
            return {"offline_guard": "pass"}
        raise RuntimeError("Python socket guard was not installed before worker import")

    if job in {"target_smoke", "target_infer", "target_validate", "reproduce"}:
        if os.environ.get("MALWAROUS_SAFE_RUNNER") != "1" or not _offline_guard_passes():
            raise RuntimeError("target jobs require the status-only offline runner")

    if job == "target_smoke":
        _locked_window()
        _require_target_assets()
        return {"inputs_present": "pass", "offline_guard": "pass"}

    if job == "target_infer":
        _generate_locked_submission(PRIVATE_OUTPUT)
        valid = _validate_submission(PRIVATE_OUTPUT)
        return {
            "frame_contract": "pass" if valid else "fail",
            "csv_contract": "pass" if valid else "fail",
        }

    if job == "target_validate":
        _locked_window()
        valid = _validate_submission(PRIVATE_OUTPUT)
        return {
            "frame_contract": "pass" if valid else "fail",
            "csv_contract": "pass" if valid else "fail",
        }

    if job == "reproduce":
        _locked_window()
        if not PRIVATE_OUTPUT.is_file():
            raise FileNotFoundError("locked submission is not present")
        original_valid = _validate_submission(PRIVATE_OUTPUT)
        try:
            _generate_locked_submission(REPRODUCTION_OUTPUT)
            reproduced_valid = _validate_submission(REPRODUCTION_OUTPUT)
            same = (original_valid and reproduced_valid
                    and PRIVATE_OUTPUT.read_bytes() == REPRODUCTION_OUTPUT.read_bytes())
        finally:
            REPRODUCTION_OUTPUT.unlink(missing_ok=True)
        return {
            "csv_contract": "pass" if original_valid and reproduced_valid else "fail",
            "byte_reproduction": "pass" if same else "fail",
        }

    raise NotImplementedError(job)


def main() -> int:
    job, status_file = sys.argv[1], Path(sys.argv[2])
    if job not in ALLOWED_JOBS:
        _write_status(status_file, job, "failed", {}, "INTERNAL_ERROR")
        return 2
    try:
        checks = execute(job)
        if not isinstance(checks, dict):
            raise TypeError("worker must return a status check mapping")
        if any(k not in ALLOWED_CHECKS or v not in ALLOWED_STATES for k, v in checks.items()):
            raise TypeError("worker returned an unsupported check")
        failed_check = any(value == "fail" for value in checks.values())
        _write_status(
            status_file, job, "failed" if failed_check else "completed", checks,
            "INPUT_INVALID" if failed_check else None,
        )
        return 1 if failed_check else 0
    except Exception as exc:
        # The full traceback is routed to the private log by the parent. The status file contains
        # only a generic code derived from the exception type, never its message or filename.
        traceback.print_exc(file=sys.stderr)
        code = FAILURE_TYPES.get(type(exc).__name__, "INTERNAL_ERROR")
        _write_status(status_file, job, "failed", {}, code)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

