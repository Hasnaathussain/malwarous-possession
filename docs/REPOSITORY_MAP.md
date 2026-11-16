# Where to find things

| Location | Purpose |
|---|---|
| `README.md` | Installation, demonstration and exact CSV reproduction |
| `docs/TECHNICAL_NOTE.md` | Short description of the submitted method |
| `malwarous/v2/model.py` | Observable features, two classifiers and sequence decoding |
| `malwarous/v2/target_worker.py` | Checked local inference adapter |
| `malwarous/v2/safe_runner.py` | Status-only local execution entry point |
| `configs/v2_candidate.json` | Selected settings, training provenance and frozen hashes |
| `models_private/v2-possession.joblib` | The one included, external-only fitted model |
| `evaluation/` | Unmodified organizer metric and validator |
| `workbench/` | Local analyst interface and synthetic demonstration |
| `website/` | Public Possession Atlas: static replay, method guide and synthetic decoder lab |
| `website/PUBLIC_DATA.md` | Licensed public replay provenance and display transformations |
| `scripts/serve_public_site.py` | Loopback-only public website preview with video range requests |
| `scripts/export_public_site.py` | Export only the approved external and synthetic public fixtures |
| `docs/experiments/` | External development protocol and benchmark evidence |
| `docs/TEAM_COMPARISON.md` | Fair comparison of three team members' methods |
| `tests/` | Synthetic contracts, source checks and local HTTP tests |
| `SOURCE_MANIFEST.json` | Byte inventory of every other committed file |
| `scripts/verify_repository.py` | Check the tracked inventory, staged bytes and frozen artifacts |
| `scripts/release_integrity.py` | Path safety and artifact checks used by the verifier |

## Why older core/configuration names remain

The selected V2 runner checks the earlier reference pipeline's source fingerprints
as part of its integrity boundary. Older core modules, four configuration files
and reference-study helpers are required dependencies of those checks. They are
not alternative submission choices. Removing or formatting them breaks the frozen
reproduction chain. The selected method is explicitly `context_p10_r0`.

Failed experimental model versions, raw datasets, old release folders, internal
planning, meeting media, private guides and other generated target outputs are excluded; the team-published final CSV/PDF packet is the named exception.

## Files generated when you run it

Your environment is `.venv/`. Local predictions and detailed run diagnostics go in
`artifacts_private/`. External acquisition caches go in `external_data_cache/`.
These are ignored local working files and must not be committed. The included
external-only fitted model is the single intentional exception under
`models_private/`, with attribution in `MODEL_ATTRIBUTION.md`. The public website
also includes CC BY 4.0 external display replays and one hash-pinned synthetic
video, described in `website/PUBLIC_DATA.md`. These are public fixtures, not
competition assets or generated target predictions.

## One selected pipeline

`context_p10_r0` is the only shipped candidate. V1 to final changed the instantaneous emission model into 65 observation-weighted contextual features, natural-prior live/owner heads, symmetric team inference and a half-wise p10 decoder. Earlier references remain because V2 checks/imports them; see [every retained legacy dependency](FROZEN_DEPENDENCIES.md). Each listed legacy file is a frozen reproduction dependency; do not remove or re-lock it. `malwarous/v6/` is cache-only external audit code, not a target runner or alternative trained model.

From the root, create a Python3.11.9 environment and install `requirements.lock`; set `MTAH_DATA_DIR` to the separately authorized bundle. Run `python -m malwarous.v2.safe_runner v2_target_infer`, followed by `python -m malwarous.v2.safe_runner v2_target_reproduce`. Check success after each. The generated file is `artifacts_private/v2/Malwarous-v2.csv`; named final copies live in `submission/`. Use `python evaluation/validate_submission.py submission/Malwarous.csv` before the form upload. The form needs the team CSV, PDF and public repository URL; GitHub publication is not submission.

`docs/Malwarous.html` and `scripts/build_technical_pdf.mjs` build the designed technical PDF; `docs/figures/` contains public-safe showcase screenshots only. `docs/CONTINUATION_LEDGER.md` records final gates, reproduction and checklist status. The source manifest covers all committed files except itself.
