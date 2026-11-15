"""Run the predeclared external-only selection once and freeze its release candidate."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from malwarous.experiments import (
    _protocol_digest,
    _release_choice,
    _select_candidate,
    _transition_matrix,
    load_protocol,
)


CODE_INPUTS = (
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


def _json_bytes(payload: dict) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _atomic_bytes(path: Path, content: bytes) -> None:
    """Replace one file only after its complete bytes reach disk."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False
        ) as handle:
            temporary = Path(handle.name)
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _atomic_json(path: Path, payload: dict) -> None:
    _atomic_bytes(path, _json_bytes(payload))


@contextmanager
def _exclusive_run_lock():
    """Hold a cross-platform OS lock for the full selection and commit window."""
    path = ROOT / "artifacts_private" / "locks" / "external-selection.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as handle:
        if os.name == "nt":
            import msvcrt

            handle.seek(0, os.SEEK_END)
            if handle.tell() == 0:
                handle.write(b"0")
                handle.flush()
            handle.seek(0)
            try:
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as exc:
                raise RuntimeError("another selection process owns the run lock") from exc
            unlock = lambda: msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                raise RuntimeError("another selection process owns the run lock") from exc
            unlock = lambda: fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        try:
            yield
        finally:
            unlock()


def _git_commit(*, require_clean: bool) -> str:
    if require_clean:
        status = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=normal"],
            cwd=ROOT, capture_output=True, text=True, check=True, shell=False,
        )
        if status.stdout.strip():
            raise RuntimeError("commit the reviewed code before the frozen selection run")
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT,
        capture_output=True, text=True, check=True, shell=False,
    )
    return result.stdout.strip()


def _code_fingerprint() -> str:
    digest = hashlib.sha256()
    for relative in CODE_INPUTS:
        path = ROOT / relative
        content = path.read_bytes()
        encoded_name = relative.encode("utf-8")
        digest.update(len(encoded_name).to_bytes(4, "big"))
        digest.update(encoded_name)
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return digest.hexdigest()


def _utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("campaign timestamps must include a timezone")
    return parsed.astimezone(timezone.utc)


def _campaign(protocol: dict, code_commit: str, code_fingerprint: str) -> tuple[dict, datetime]:
    path = ROOT / "artifacts_private" / "selection_campaign.json"
    now = datetime.now(timezone.utc)
    cutoff_pk = datetime.strptime(
        protocol["latest_experiment_finish_pk_time"], "%Y-%m-%d %H:%M"
    ).replace(tzinfo=ZoneInfo("Asia/Karachi"))
    cutoff_utc = cutoff_pk.astimezone(timezone.utc)
    protocol_hash = _protocol_digest(protocol)
    if path.exists():
        campaign = json.loads(path.read_text(encoding="utf-8"))
        if (campaign.get("status") not in {"in_progress", "completed"} or
                campaign.get("protocol_sha256") != protocol_hash or
                campaign.get("code_commit") != code_commit or
                campaign.get("code_fingerprint") != code_fingerprint):
            raise RuntimeError("stored campaign lock belongs to different code or settings")
        attempts = campaign.get("attempt_count")
        if isinstance(attempts, bool) or not isinstance(attempts, int) or not 0 <= attempts <= 2:
            raise RuntimeError("stored campaign attempt counter is invalid")
        started = _utc(campaign["started_at_utc"])
        deadline = min(
            started + timedelta(hours=float(protocol["experiment_cap_hours"])), cutoff_utc
        )
        if campaign.get("deadline_utc") != deadline.isoformat(timespec="seconds"):
            raise RuntimeError("stored campaign deadline is invalid")
    else:
        started = now.replace(microsecond=0)
        deadline = min(
            started + timedelta(hours=float(protocol["experiment_cap_hours"])), cutoff_utc
        )
        campaign = {
            "status": "in_progress",
            "protocol_sha256": protocol_hash,
            "code_commit": code_commit,
            "code_fingerprint": code_fingerprint,
            "started_at_utc": started.isoformat(timespec="seconds"),
            "deadline_utc": deadline.isoformat(timespec="seconds"),
            "attempt_count": 0,
        }
        _atomic_json(path, campaign)
    if now >= deadline:
        raise TimeoutError("the frozen campaign budget or cutoff has expired")
    return campaign, deadline


def _selection_child_environment() -> dict[str, str]:
    env = {key: os.environ[key] for key in (
        "PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "PATHEXT",
    ) if key in os.environ}
    env.update({
        "PYTHONNOUSERSITE": "1",
        "PYTHONHASHSEED": "0",
        "OMP_NUM_THREADS": "1",
        "OPENBLAS_NUM_THREADS": "1",
        "MKL_NUM_THREADS": "1",
        "NUMEXPR_MAX_THREADS": "1",
    })
    return env


def _run_selection_preflight(protocol: dict) -> None:
    """Import the frozen stack offline before any campaign budget or source parse begins."""
    log_path = ROOT / "artifacts_private" / "runs" / "external-selection-preflight.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable, "-s", str(ROOT / "scripts" / "compute_external_selection.py"), "--preflight"
    ]
    with log_path.open("wb") as log:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            env=_selection_child_environment(),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=log,
            timeout=120,
            check=False,
            shell=False,
            text=True,
            encoding="utf-8",
        )
    if completed.returncode != 0:
        raise RuntimeError("external selection preflight failed")
    try:
        result = json.loads(completed.stdout)
    except (json.JSONDecodeError, TypeError) as exc:
        raise RuntimeError("external selection preflight returned no valid status") from exc
    if (not isinstance(result, dict) or result.get("status") != "ready" or
            result.get("protocol_sha256") != _protocol_digest(protocol)):
        raise RuntimeError("external selection preflight failed the pinned contract")


def _run_selection_child(timeout_seconds: float, protocol: dict) -> dict:
    """Run all parsing/fitting/scoring in a child with a parent-enforced absolute timeout."""
    if timeout_seconds <= 60:
        raise TimeoutError("insufficient remaining campaign time to run selection safely")
    log_path = ROOT / "artifacts_private" / "runs" / "external-selection-child.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    # `-s` disables user site-packages without suppressing PYTHONHASHSEED; the sanitized
    # environment has no PYTHONPATH, so this still preserves isolation and repeatability.
    command = [sys.executable, "-s", str(ROOT / "scripts" / "compute_external_selection.py")]
    with log_path.open("wb") as log:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            env=_selection_child_environment(),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=log,
            timeout=timeout_seconds - 60.0,
            check=False,
            shell=False,
            text=True,
            encoding="utf-8",
        )
    if completed.returncode != 0:
        raise RuntimeError("external selection child did not complete")
    try:
        result = json.loads(completed.stdout)
    except (json.JSONDecodeError, TypeError) as exc:
        raise RuntimeError("external selection child returned no valid result") from exc
    if (not isinstance(result, dict) or result.get("status") != "completed" or
            result.get("protocol_sha256") != _protocol_digest(protocol)):
        raise RuntimeError("external selection child result failed the pinned contract")
    return result


def _report_is_valid(report: dict, protocol: dict, code_commit: str,
                     code_fingerprint: str) -> bool:
    try:
        if (report.get("status") != "completed" or
                report.get("protocol_sha256") != _protocol_digest(protocol) or
                report.get("code_commit") != code_commit or
                report.get("code_fingerprint") != code_fingerprint or
                report.get("training_matches") != protocol["training_matches_for_selection"] or
                report.get("selection_matches") != protocol["selection_matches"] or
                report.get("sealed_match_accessed") is not False):
            return False
        _utc(report["locked_at_utc"])
        _utc(report["campaign_started_at_utc"])
        conditions = [item["name"] for item in protocol["corruption"]["conditions"]]
        matches = protocol["selection_matches"]
        candidates = [item["name"] for item in protocol["decoder_candidates"]]
        expected_pairs = {(match, condition) for match in matches for condition in conditions}
        validation_rows = report["validation_rows"]
        reference_rows = report["reference_rows"]
        summary = report["selection_summary"]
        if len(reference_rows) != len(expected_pairs) or {
            (row["match"], row["corruption"]) for row in reference_rows
        } != expected_pairs:
            return False
        if len(summary) != len(candidates) or {
            row["candidate"] for row in summary
        } != set(candidates):
            return False
        if len(validation_rows) != len(candidates) * len(expected_pairs):
            return False
        for name in candidates:
            rows = [row for row in validation_rows if row["candidate"] == name]
            if {(row["match"], row["corruption"]) for row in rows} != expected_pairs:
                return False
            summary_row = next(row for row in summary if row["candidate"] == name)
            if summary_row.get("evaluations") != len(expected_pairs):
                return False
            for summary_key, row_key in (
                ("mean_spell_f1", "spell_f1"),
                ("mean_macro_f1", "macro_f1"),
            ):
                calculated = math.fsum(float(row[row_key]) for row in rows) / len(rows)
                if not math.isclose(
                    float(summary_row[summary_key]), calculated,
                    rel_tol=0.0, abs_tol=1e-12,
                ):
                    return False
        score_values = [
            row[key]
            for row in validation_rows + reference_rows
            for key in ("spell_f1", "macro_f1")
        ]
        score_values.extend(
            row[key]
            for row in summary
            for key in ("mean_spell_f1", "mean_macro_f1")
        )
        if not all(isinstance(value, (int, float)) and math.isfinite(value)
                   for value in score_values):
            return False
        summary_by_name = {row["candidate"]: row for row in summary}
        selected = _select_candidate(summary, protocol)
        if report.get("selected_candidate") != selected["candidate"]:
            return False
        reference_mean = math.fsum(row["spell_f1"] for row in reference_rows) / len(reference_rows)
        if not math.isclose(
            float(report["reference_mean_spell_f1"]), reference_mean,
            rel_tol=0.0, abs_tol=1e-12,
        ):
            return False
        release_candidate, release_mode = _release_choice(
            summary_by_name[selected["candidate"]], reference_mean
        )
        return (report.get("release_candidate") == release_candidate and
                report.get("release_mode") == release_mode)
    except (KeyError, TypeError, ValueError, OverflowError, ZeroDivisionError):
        return False


def _remove_interrupted_temps(report_path: Path, final_path: Path, pending_path: Path) -> None:
    """Remove only this script's atomic-write leftovers while holding its run lock."""
    for target in (report_path, final_path, pending_path):
        for temporary in target.parent.glob(f".{target.name}.*.tmp"):
            temporary.unlink(missing_ok=True)


def _start_attempt(campaign: dict, campaign_path: Path) -> dict:
    attempts = int(campaign["attempt_count"])
    if attempts >= 2:
        raise RuntimeError("the frozen experiment reached its bounded retry limit")
    campaign["attempt_count"] = attempts + 1
    campaign["last_attempt_started_at_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    _atomic_json(campaign_path, campaign)
    return campaign


def _recover_completed_candidate(
    report_path: Path,
    pending_path: Path,
    final_path: Path,
    campaign: dict,
    campaign_deadline: datetime,
    protocol: dict,
    code_commit: str,
    code_fingerprint: str,
) -> int:
    if campaign.get("status") != "completed":
        print(json.dumps({"status": "failed", "failure_type": "MissingCompletionMarker"}))
        return 1
    if report_path.exists():
        report_bytes = report_path.read_bytes()
    elif pending_path.exists():
        report_bytes = pending_path.read_bytes()
        if hashlib.sha256(report_bytes).hexdigest() != campaign.get("report_sha256"):
            print(json.dumps({"status": "failed", "failure_type": "ReportDigestMismatch"}))
            return 1
        os.replace(pending_path, report_path)
    else:
        print(json.dumps({"status": "failed", "failure_type": "MissingSelectionReport"}))
        return 1
    if hashlib.sha256(report_bytes).hexdigest() != campaign.get("report_sha256"):
        print(json.dumps({"status": "failed", "failure_type": "ReportDigestMismatch"}))
        return 1
    report = json.loads(report_bytes.decode("utf-8"))
    report_is_before_deadline = (
        report.get("campaign_started_at_utc") == campaign["started_at_utc"] and
        report.get("locked_at_utc") == campaign.get("locked_at_utc") and
        _utc(campaign.get("completed_at_utc", "1970-01-01T00:00:00+00:00")) <= campaign_deadline and
        _utc(report.get("locked_at_utc", "1970-01-01T00:00:00+00:00")) <= campaign_deadline
    )
    if (not report_is_before_deadline or
            not _report_is_valid(report, protocol, code_commit, code_fingerprint)):
        print(json.dumps({"status": "failed", "failure_type": "UnrecoverableSelectionReport"}))
        return 1
    pending_path.unlink(missing_ok=True)
    _atomic_json(final_path, _final_candidate(report, protocol))
    print(json.dumps({
        "status": "completed",
        "selected_candidate": report["selected_candidate"],
        "release_candidate": report["release_candidate"],
        "release_mode": report["release_mode"],
        "protocol_sha256": report["protocol_sha256"],
        "selection_summary": report["selection_summary"],
        "reference_mean_spell_f1": report["reference_mean_spell_f1"],
        "recovered_lock": True,
    }, sort_keys=True))
    return 0


def _run_and_lock_candidate(
    report_path: Path,
    pending_path: Path,
    final_path: Path,
    campaign_path: Path,
    campaign: dict,
    campaign_deadline: datetime,
    protocol: dict,
    code_commit: str,
    code_fingerprint: str,
) -> int:
    remaining = (campaign_deadline - datetime.now(timezone.utc)).total_seconds()
    result = _run_selection_child(remaining, protocol)
    if datetime.now(timezone.utc) >= campaign_deadline:
        raise TimeoutError("the frozen campaign budget or cutoff expired before selection lock")
    if (_git_commit(require_clean=True) != code_commit or
            _code_fingerprint() != code_fingerprint or
            _protocol_digest(load_protocol(ROOT / "configs" / "experiment_protocol.json")) !=
            _protocol_digest(protocol)):
        raise RuntimeError("reviewed code or protocol changed during the selection run")
    result["locked_at_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    result["campaign_started_at_utc"] = campaign["started_at_utc"]
    result["code_commit"] = code_commit
    result["code_fingerprint"] = code_fingerprint
    if not _report_is_valid(result, protocol, code_commit, code_fingerprint):
        raise RuntimeError("completed external selection failed its report contract")

    report_bytes = _json_bytes(result)
    _atomic_bytes(pending_path, report_bytes)
    if datetime.now(timezone.utc) >= campaign_deadline:
        raise TimeoutError("the frozen campaign deadline expired before the result marker")
    if (_git_commit(require_clean=False) != code_commit or
            _code_fingerprint() != code_fingerprint or
            _protocol_digest(load_protocol(ROOT / "configs" / "experiment_protocol.json")) !=
            _protocol_digest(protocol)):
        raise RuntimeError("reviewed code or protocol changed before the completion marker")
    campaign.update({
        "status": "completed",
        "locked_at_utc": result["locked_at_utc"],
        "completed_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "report_sha256": hashlib.sha256(report_bytes).hexdigest(),
    })
    _atomic_json(campaign_path, campaign)
    if datetime.now(timezone.utc) >= campaign_deadline:
        raise TimeoutError("the frozen campaign deadline expired while writing the result marker")
    os.replace(pending_path, report_path)
    if datetime.now(timezone.utc) >= campaign_deadline:
        raise TimeoutError("the frozen campaign deadline expired before the candidate lock")
    _atomic_json(final_path, _final_candidate(result, protocol))
    print(json.dumps({
        "status": "completed",
        "selected_candidate": result["selected_candidate"],
        "release_candidate": result["release_candidate"],
        "release_mode": result["release_mode"],
        "protocol_sha256": result["protocol_sha256"],
        "selection_summary": result["selection_summary"],
        "reference_mean_spell_f1": result["reference_mean_spell_f1"],
    }, sort_keys=True))
    return 0


def _final_candidate(result: dict, protocol: dict) -> dict:
    definition = next((candidate for candidate in protocol["decoder_candidates"]
                       if candidate["name"] == result["release_candidate"]), None)
    final = {
        "lock_id": protocol["protocol_id"],
        "locked_at_utc": result["locked_at_utc"],
        "protocol_sha256": result["protocol_sha256"],
        "code_commit": result["code_commit"],
        "code_fingerprint": result["code_fingerprint"],
        "campaign_started_at_utc": result["campaign_started_at_utc"],
        "candidate": result["release_candidate"],
        "mode": result["release_mode"],
        "candidate_definition": definition,
        "reference_window": 50 if result["release_mode"] == "reference" else None,
        "training_matches": protocol["development_matches"],
        "sealed_audit_match": protocol["sealed_audit_match"],
        "sealed_audit_policy": protocol["sealed_audit_policy"],
    }
    if definition is not None:
        final["transition_log_scores"] = _transition_matrix(definition).tolist()
    return final


def main() -> int:
    config_path = ROOT / "configs" / "experiment_protocol.json"
    final_path = ROOT / "configs" / "final_candidate.json"
    report_path = ROOT / "docs" / "experiments" / "selection-v1.json"
    try:
        with _exclusive_run_lock():
            return _run_locked(config_path, final_path, report_path)
    except RuntimeError as exc:
        failure = "ConcurrentRun" if "owns the run lock" in str(exc) else type(exc).__name__
        print(json.dumps({"status": "failed", "failure_type": failure}))
        return 1
    except Exception as exc:
        print(json.dumps({"status": "failed", "failure_type": type(exc).__name__}))
        return 1


def _run_locked(config_path: Path, final_path: Path, report_path: Path) -> int:
    protocol = load_protocol(config_path)
    pending_path = report_path.with_name(f".{report_path.name}.pending")
    campaign_path = ROOT / "artifacts_private" / "selection_campaign.json"
    _remove_interrupted_temps(report_path, final_path, pending_path)
    if final_path.exists():
        print(json.dumps({"status": "failed", "failure_type": "LockAlreadyExists"}))
        return 1

    recovery_attempt = report_path.exists() or pending_path.exists()
    if recovery_attempt and not campaign_path.exists():
        print(json.dumps({"status": "failed", "failure_type": "MissingCampaignLedger"}))
        return 1
    code_commit = _git_commit(require_clean=not recovery_attempt)
    code_fingerprint = _code_fingerprint()
    if not report_path.exists():
        campaign_complete = False
        if campaign_path.exists():
            try:
                campaign_complete = json.loads(
                    campaign_path.read_text(encoding="utf-8")
                ).get("status") == "completed"
            except (OSError, json.JSONDecodeError):
                campaign_complete = False
        if not campaign_complete:
            _run_selection_preflight(protocol)
    campaign, campaign_deadline = _campaign(protocol, code_commit, code_fingerprint)
    if campaign.get("status") == "completed":
        return _recover_completed_candidate(
            report_path, pending_path, final_path, campaign, campaign_deadline,
            protocol, code_commit, code_fingerprint,
        )
    if report_path.exists():
        print(json.dumps({"status": "failed", "failure_type": "MissingCompletionMarker"}))
        return 1
    if pending_path.exists():
        # A pending report without a completion marker is never promoted. Drop that uncommitted
        # artifact and allow one identical, seeded retry within the original campaign budget.
        pending_path.unlink()
        if (_git_commit(require_clean=True) != code_commit or
                _code_fingerprint() != code_fingerprint):
            raise RuntimeError("reviewed code changed before the bounded retry")
    campaign = _start_attempt(campaign, campaign_path)
    return _run_and_lock_candidate(
        report_path, pending_path, final_path, campaign_path, campaign,
        campaign_deadline, protocol, code_commit, code_fingerprint,
    )


if __name__ == "__main__":
    raise SystemExit(main())
