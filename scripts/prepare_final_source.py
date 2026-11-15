"""Create the concise final source edition without changing the research checkout.

Only explicit source names and approved text trees are read. No target output,
competition asset, cache or old release is copied. No Git operation is performed.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if __name__ == '__main__':
    # Verifying a pristine edition must not dirty its inventory by importing this
    # builder's helper into a newly created scripts/__pycache__ directory.
    sys.dont_write_bytecode = True
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts import prepare_review_source as review

CORE = {
    'pytest.ini',
    'LICENSE', 'games.py', 'requirements.txt', 'requirements.in',
    'requirements.lock', 'requirements-test.in', 'requirements-starter.txt',
    'configs/experiment_protocol.json', 'configs/final_candidate.json',
    'configs/target_runner_lock.json', 'configs/v2_candidate.json',
    'evaluation/possession_metrics.py', 'evaluation/validate_submission.py',
    'malwarous/__init__.py', 'malwarous/corruption.py', 'malwarous/experiments.py',
    'malwarous/external_pipeline.py', 'malwarous/external_sportec.py',
    'malwarous/features.py', 'malwarous/models.py', 'malwarous/temporal.py',
    'malwarous/inference.py', 'malwarous/metrica_ingest.py',
    'malwarous/private_worker.py', 'malwarous/safe_runner.py',
    'starter/baseline.py',
    'scripts/run_external_experiments.py', 'scripts/compute_external_selection.py',
    'scripts/fetch_sportec.py', 'scripts/export_workbench_benchmarks.py',
    'scripts/check_workbench_browser.mjs', 'scripts/prepare_review_source.py',
    'scripts/prepare_final_source.py', 'scripts/compare_team_models.py',
    'configs/team_comparison.example.json',
    'docs/V2_GUIDE.md', 'docs/V2_PROVENANCE.md', 'docs/TEAM_COMPARISON.md',
    'docs/FINAL_SUMMARY.md',
    'docs/experiments/V2_STUDY.md', 'docs/experiments/V2_RESULTS.md',
    'docs/experiments/V2_DIAGNOSIS.md', 'docs/experiments/V2_DATA_REVIEW.md',
    'docs/experiments/v2-results.json', 'docs/experiments/v2-benchmarks.json',
    'docs/experiments/FINAL_EXTERNAL_RESULTS.md',
    'docs/experiments/FINAL_EXTERNAL_CHECK.md',
    'docs/experiments/final-external-results.json',
    review.MODEL,
}
TESTS = {
    'test_corruption.py', 'test_external_pipeline.py', 'test_external_sportec.py',
    'test_features.py', 'test_fetch_sportec.py', 'test_inference.py',
    'test_malwarous_contract.py', 'test_metrica_ingest.py', 'test_models.py',
    'test_safe_runner.py', 'test_temporal.py', 'test_v2_boundary.py',
    'test_v2_model.py', 'test_v2_offline.py', 'test_workbench.py',
    'test_team_comparison.py', 'test_final_source.py',
}
TREES = {'malwarous/v2': {'.py'}, 'workbench': {'.py', '.md', '.json', '.js', '.css', '.html'}}

README = '''# Malwarous

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

Use 64-bit Python 3.11.9. Work from a copy of this source folder, leaving the
reviewed delivery unchanged.

```powershell
python -m venv .venv
.\\.venv\\Scripts\\python.exe -m pip install -r requirements.lock
.\\.venv\\Scripts\\python.exe -m pip install -r requirements-test.in
.\\.venv\\Scripts\\python.exe -m pytest -q
.\\.venv\\Scripts\\python.exe -m workbench.server --port 8765
```

Open http://127.0.0.1:8765 for the generated synthetic demo. Its labels are authored
software fixtures and its score cells are empty. The workbench has synchronized
playback, frame navigation, evidence plots, provenance and keyboard controls.
[Workbench guide](workbench/README.md).

## Reproduce the submission locally

The checked external-only fitted weights are included. **Do not run a training or
finalizer command for setup.** Obtain the competition assets separately under the
organizer's accepted terms and set their root:

```powershell
$env:MTAH_DATA_DIR='D:\\path\\to\\authorized\\bundle'
.\\.venv\\Scripts\\python.exe -m malwarous.v2.safe_runner v2_target_infer
.\\.venv\\Scripts\\python.exe -m malwarous.v2.safe_runner v2_target_reproduce
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

This edition contains the selected algorithm and its dependencies. Older-named
core modules/configs remain because the frozen runner verifies/imports them.
Failed experimental versions, duplicate release folders, private planning, caches
and raw data are excluded. The internal research workspace retains the full audit.

`SOURCE_MANIFEST.json` fingerprints every other delivered file. Verify this edition
without a Git repository or the original research workspace:

```powershell
python -B scripts/prepare_final_source.py --destination . --verify-only
```

Creating another edition from the internal checkout requires its selected source
files. The builder refuses nonempty destinations; it never merges, deletes, makes
a commit or publishes. `.gitattributes` preserves raw mixed LF/CRLF bytes required
by frozen source hashes; do not run a line-ending formatter over locked sources.

Code retains the organizer MIT notice in [LICENSE](LICENSE). External derived
weights/results require the CC BY 4.0 credit in [MODEL_ATTRIBUTION.md](MODEL_ATTRIBUTION.md).
Competition assets have separate restricted terms and are not included.
'''

IGNORE = '''# Competition assets, predictions and local working state never belong in Git.
/data/
/tactical/
/broadcast/
/artifacts_private/
/external_data_cache/
/models_private/*
!/models_private/v2-possession.joblib
/.venv/
venv/
__pycache__/
.pytest_cache/
*.py[cod]
.env
.env.*
*.csv
*.mp4
*.webm
*.gzip
*.pl3container
*.joblib
!/models_private/v2-possession.joblib
*.log
*.pdf
node_modules/
.DS_Store
'''


def source_inventory(root: Path) -> set[str]:
    paths = set(CORE) | {'tests/' + name for name in TESTS}
    # Optional extra accessibility contracts are independent of the frozen model.
    if (root / 'tests/test_workbench_final.py').is_file():
        paths.add('tests/test_workbench_final.py')
    for tree, suffixes in TREES.items():
        folder = root / tree
        if folder.is_symlink() or not folder.is_dir():
            raise ValueError('approved source tree is missing or linked')
        for file in folder.rglob('*'):
            relative = file.relative_to(root).as_posix()
            if any(part.casefold() in review.FORBIDDEN_PARTS for part in file.relative_to(root).parts):
                continue
            if file.is_file() and file.suffix in suffixes:
                review.checked_file(root, relative)
                paths.add(relative)
    for name in paths:
        review.checked_file(root, name)
    return paths


def prepare(root: Path, destination: Path) -> dict:
    root = root.resolve(strict=True)
    review.validate_destination(destination, root)
    paths = source_inventory(root)
    review.verify_frozen_v2(root, paths)
    generated = {
        '.gitattributes': b'# Preserve frozen source bytes.\n* -text\n',
        '.gitignore': IGNORE.encode('utf-8'),
        'README.md': README.encode('utf-8'),
        'MODEL_ATTRIBUTION.md': review.MODEL_CREDIT.encode('utf-8'),
        'docs/TECHNICAL_NOTE.md': review.source_bytes(root, 'docs/V2_TECHNICAL_NOTE.md'),
    }
    manifest = review.write_bundle(root, destination, paths, paths, generated)
    # This edition has its own explicit inventory; the fallback commit is lineage,
    # not a claim that the final allowlist was read from that commit's Git tree.
    manifest['purpose'] = 'final selected-method source edition; no publication'
    manifest['edition'] = 'final-selected-v2'
    manifest['preserved_fallback_commit'] = manifest.pop('base_allowlist_commit')
    (destination / review.MANIFEST).write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    review.verify_bundle(destination)
    review.verify_frozen_v2(destination, {entry['path'] for entry in manifest['files']})
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=ROOT)
    parser.add_argument('--destination', type=Path, default=ROOT.parent / 'FINAL' / 'source')
    parser.add_argument('--verify-only', action='store_true')
    args = parser.parse_args()
    manifest = review.verify_bundle(args.destination) if args.verify_only else prepare(args.repo, args.destination)
    review.verify_frozen_v2(args.destination, {entry['path'] for entry in manifest['files']})
    print(json.dumps({'status': 'verified' if args.verify_only else 'prepared',
                      'files': len(manifest['files']) + 1}, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
