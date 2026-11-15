# Malwarous

Possession inference from incomplete football tracking, with a local analysis workbench.

The frozen candidate is **context_p10_r0**: two contextual tree classifiers and
half-wise persistent decoding. It uses 65 observable features, team symmetry and
explicit observation support. It is an **offline** method using future context.

| Matched external development | spellF1 | macroF1 |
|---|---:|---:|
| smooth50 reference | 0.25548 | 0.39809 |
| frozen candidate | 0.48095 | 0.86868 |

Six previously consumed DFL matches, three whole-match excluded folds and three
observation scenarios. These are selection-conditioned development measurements,
not blind-test results or competition scores. See [results](docs/FINAL_SUMMARY.md).

## Start

Use 64-bit Python 3.11.9 and the pinned dependencies. From the repository root:

Linux/macOS:

```sh
python3.11 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
.venv/bin/python -m pip install -r requirements-test.in
.venv/bin/python -m pytest -q
.venv/bin/python -m workbench.server --port 8765
```

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock
.\.venv\Scripts\python.exe -m pip install -r requirements-test.in
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m workbench.server --port 8765
```

Open http://127.0.0.1:8765 for the generated synthetic demo. Its labels are authored
software fixtures and its score cells are empty. The workbench has synchronized
playback, frame navigation, evidence plots, provenance and keyboard controls.
[Workbench guide](workbench/README.md).

## Reproduce the submission locally

The checked external-only fitted weights are included. **Do not run a training or
finalizer command for setup.** Obtain the competition assets separately under the
organizer's accepted terms and set their root:

Linux/macOS:

```sh
export MTAH_DATA_DIR='/path/to/authorized/bundle'
.venv/bin/python -m malwarous.v2.safe_runner v2_target_infer
.venv/bin/python -m malwarous.v2.safe_runner v2_target_reproduce
```

Windows PowerShell:

```powershell
$env:MTAH_DATA_DIR='D:\path\to\authorized\bundle'
.\.venv\Scripts\python.exe -m malwarous.v2.safe_runner v2_target_infer
.\.venv\Scripts\python.exe -m malwarous.v2.safe_runner v2_target_reproduce
```

Check that each command succeeds before advancing. The first writes the private
`artifacts_private/v2/Malwarous-v2.csv`; the second independently regenerates it and
requires byte identity. No target score is computed or reported. Source, report,
configuration and model hashes are checked before target processing.

Keep generated outputs and assets out of public Git. The optional private viewer
export is `python -m malwarous.v2.safe_runner v2_local_viewer_export`; its files are
for local human inspection only. Never send its bundle or viewport to a hosted
model. Browser QA is for synthetic or licensed public-external fixtures only.

## Read

- [Technical note](docs/TECHNICAL_NOTE.md): the actual submission method.
- [Model guide](docs/V2_GUIDE.md): features, inference and external reproduction.
- [Data and model provenance](docs/V2_PROVENANCE.md) and [attribution](MODEL_ATTRIBUTION.md).
- [Team comparison](docs/TEAM_COMPARISON.md): compare external predictions fairly.
- [Repository map](docs/REPOSITORY_MAP.md): the purpose of each folder and older dependency names.
- [Security](SECURITY.md) and [release checks](docs/RELEASE_CHECKS.md).

The organizer requires a **public repository URL for submission**. Keep this
repository private during team review if desired, then make the reviewed code
public before submitting the form. Competition assets and generated target CSVs
stay outside Git history regardless of repository visibility. The CSV and short
technical document go to the organizer form separately.

This edition contains the selected algorithm and its dependencies. Older-named
core modules/configs remain because the frozen runner verifies/imports them.
Failed experimental versions, duplicate release folders, private planning, caches
and raw data are excluded. The internal research workspace retains the full audit.

`SOURCE_MANIFEST.json` fingerprints every other committed file. Verify a clone:

```powershell
python -B scripts/verify_repository.py
```

The verifier checks the tracked inventory and raw source/report/model hashes;
ignored environments, logs and generated outputs are not committed source. Older
packaging helpers describe the pre-Git source edition; use `verify_repository.py`
for this repository. `.gitattributes` preserves mixed LF/CRLF bytes required by
frozen hashes. Do not run a line-ending formatter over locked sources.

Exact target-byte reproduction was verified on Windows with CPython 3.11.9.
The standalone replay also passed Ubuntu preflight checks. Cross-platform ML
byte identity has not been independently established; preserve the verified
environment when regenerating the selected submission file.

Code retains the organizer MIT notice in [LICENSE](LICENSE). External derived
weights/results require the CC BY 4.0 credit in [MODEL_ATTRIBUTION.md](MODEL_ATTRIBUTION.md).
Competition assets have separate restricted terms and are not included.
