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
| `docs/experiments/` | External development protocol and benchmark evidence |
| `docs/TEAM_COMPARISON.md` | Fair comparison of three team members' methods |
| `tests/` | Synthetic contracts, source checks and local HTTP tests |
| `SOURCE_MANIFEST.json` | Byte inventory of every other committed file |

## Why older core/configuration names remain

The selected V2 runner checks the earlier reference pipeline's source fingerprints
as part of its integrity boundary. Older core modules, four configuration files
and reference-study helpers are required dependencies of those checks. They are
not alternative submission choices. Removing or formatting them breaks the frozen
reproduction chain. The selected method is explicitly `context_p10_r0`.

Failed experimental model versions, raw datasets, old release folders, internal
planning, meeting media, private guides and generated target outputs are excluded.

## Files generated when you run it

Your environment is `.venv/`. Local predictions and detailed run diagnostics go in
`artifacts_private/`. External acquisition caches go in `external_data_cache/`.
These are ignored local working files and must not be committed. The included
external-only fitted model is the single intentional exception under
`models_private/`, with attribution in `MODEL_ATTRIBUTION.md`.
