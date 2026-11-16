# Frozen dependency ledger

The table records 19 legacy dependencies plus the current V2 configuration. Legacy names are dependencies, not alternative submission choices. Do not remove, rename, format or re-lock these files. The shipped method is `context_p10_r0`.

V2 calls `malwarous.private_worker._locked_window()`, which verifies the earlier protocol and runner lock. The V2 config additionally pins 21 study/target source files. Every tracked file is covered by `SOURCE_MANIFEST.json`; `.gitattributes` keeps raw line endings.

| File | Lock/import dependants (explicit references) | Retention reason |
|---|---|---|
| `configs/experiment_protocol.json` | `configs/target_runner_lock.json`, `malwarous/private_worker.py`; source manifest | Inherited V1 protocol/runner hash chain; do not remove |
| `configs/final_candidate.json` | `malwarous/private_worker.py:_locked_window()` reads it using a joined path; source manifest | Inherited V1 protocol/runner hash chain; do not remove |
| `configs/target_runner_lock.json` | `configs/final_candidate.json:target_runner_lock_sha256`, `malwarous/private_worker.py:_locked_window()`; source manifest | Inherited V1 protocol/runner hash chain; do not remove |
| `configs/v2_candidate.json` | `docs/REPOSITORY_MAP.md`, `docs/V2_PROVENANCE.md`, `malwarous/v2/finalize.py`, `malwarous/v2/target_worker.py`, `scripts/release_integrity.py`, `tests/test_v2_boundary.py`; source manifest | Current V2 configuration, checked by the selected runner; do not remove |
| `malwarous/__init__.py` | `configs/target_runner_lock.json`, `malwarous/private_worker.py`; source manifest | Package marker and inherited runner hash lock; do not remove |
| `malwarous/corruption.py` | `configs/v2_candidate.json`, `malwarous/experiments.py`, `malwarous/external_pipeline.py`, `malwarous/private_worker.py`, `malwarous/v2/study.py`, `scripts/release_integrity.py`, `scripts/run_external_experiments.py`; source manifest | V2 source hash lock; do not remove |
| `malwarous/experiments.py` | `malwarous/private_worker.py`, `scripts/compute_external_selection.py`, `scripts/run_external_experiments.py`, `tests/test_external_pipeline.py`; source manifest | Inherited V1 protocol/runner hash chain; do not remove |
| `malwarous/external_pipeline.py` | `configs/v2_candidate.json`, `malwarous/experiments.py`, `malwarous/private_worker.py`, `malwarous/v2/export.py`, `malwarous/v2/study.py`, `scripts/release_integrity.py`, `scripts/run_external_experiments.py`; source manifest | V2 source hash lock; do not remove |
| `malwarous/external_sportec.py` | `configs/v2_candidate.json`, `malwarous/corruption.py`, `malwarous/external_pipeline.py`, `malwarous/private_worker.py`, `malwarous/v2/study.py`, `scripts/release_integrity.py`, `scripts/run_external_experiments.py`; source manifest | V2 source hash lock; do not remove |
| `malwarous/features.py` | `configs/experiment_protocol.json`, `configs/target_runner_lock.json`, `configs/v2_candidate.json`, `malwarous/experiments.py`, `malwarous/external_pipeline.py`, `malwarous/inference.py`, `malwarous/models.py`; source manifest | V2 source hash lock; do not remove |
| `malwarous/inference.py` | `configs/target_runner_lock.json`, `configs/v2_candidate.json`, `malwarous/private_worker.py`, `malwarous/v2/target_worker.py`, `scripts/release_integrity.py`, `tests/test_inference.py`; source manifest | V2 source hash lock; do not remove |
| `malwarous/metrica_ingest.py` | `configs/target_runner_lock.json`, `configs/v2_candidate.json`, `malwarous/inference.py`, `malwarous/private_worker.py`, `malwarous/v2/target_worker.py`, `scripts/release_integrity.py`, `tests/test_inference.py`; source manifest | V2 source hash lock; do not remove |
| `malwarous/models.py` | `configs/target_runner_lock.json`, `malwarous/experiments.py`, `malwarous/external_pipeline.py`, `malwarous/inference.py`, `malwarous/private_worker.py`, `scripts/run_external_experiments.py`, `tests/test_inference.py`; source manifest | Inherited V1 protocol/runner hash chain; do not remove |
| `malwarous/private_worker.py` | `configs/target_runner_lock.json`, `malwarous/safe_runner.py`, `malwarous/v2/target_worker.py`; source manifest | Inherited V1 protocol/runner hash chain; do not remove |
| `malwarous/safe_runner.py` | `configs/target_runner_lock.json`, `malwarous/private_worker.py`, `malwarous/v2/safe_runner.py`, `malwarous/v2/target_worker.py`, `tests/test_safe_runner.py`, `tests/test_v2_offline.py`; source manifest | Inherited V1 protocol/runner hash chain; do not remove |
| `malwarous/temporal.py` | `configs/target_runner_lock.json`, `configs/v2_candidate.json`, `malwarous/experiments.py`, `malwarous/external_pipeline.py`, `malwarous/inference.py`, `malwarous/private_worker.py`, `malwarous/v2/model.py`; source manifest | V2 source hash lock; do not remove |
| `scripts/compute_external_selection.py` | `malwarous/private_worker.py`, `scripts/run_external_experiments.py`; source manifest | Inherited V1 protocol/runner hash chain; do not remove |
| `scripts/fetch_sportec.py` | `malwarous/external_pipeline.py`, `malwarous/private_worker.py`, `scripts/run_external_experiments.py`, `tests/test_fetch_sportec.py`; source manifest | Inherited V1 protocol/runner hash chain; do not remove |
| `scripts/run_external_experiments.py` | `malwarous/private_worker.py`; source manifest | Inherited V1 protocol/runner hash chain; do not remove |
| `starter/baseline.py` | `configs/target_runner_lock.json`, `configs/v2_candidate.json`, `malwarous/external_pipeline.py`, `malwarous/private_worker.py`, `malwarous/v2/study.py`, `scripts/release_integrity.py`, `scripts/run_external_experiments.py`; source manifest | V2 source hash lock; do not remove |

## Cleanup decision

No tracked legacy module was deleted. A filename without a direct Python import can still be hash-locked by `_locked_window`; the lock chain takes precedence. Caches, logs, environments, private planning and failed V3/V4/V5 implementation folders are not tracked in this source edition. The V6 namespace is a cache-only diagnostic audit, not a replacement model.

The `.gitattributes` rules preserve all source bytes; they suppress diffs for the final CSV/PDF, and permit CR line endings in the integrity helper. Do not normalize frozen files.
