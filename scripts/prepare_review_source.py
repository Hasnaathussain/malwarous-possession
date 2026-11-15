"""Prepare an allowlisted, data-free local review folder; never create Git history.

The v1 snapshot supplies names and its safe ignore policy only. Current source is
copied as raw bytes from the internal repository so frozen V2 hashes survive.
No match assets, target predictions, logs or private viewer bundles are opened.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import stat
import subprocess

V1_HEAD = '42f487187dbd9f8cd1ee75cc201e3e2952b7103f'
MODEL = 'models_private/v2-possession.joblib'
MODEL_SHA256 = 'c6deb427e42dca2b2d35ffa47576f4fbb94509729c0216b46312b1f367c2418d'
REPORT_SHA256 = '743702395ee6e95a6bb769608527af95423c8ab7b34903182783241d6ff9e8e8'
MATCHES = ['J03WN1', 'J03WOY', 'J03WPY', 'J03WOH', 'J03WQQ', 'J03WR9']
STUDY_INPUTS = {
    'evaluation/possession_metrics.py', 'malwarous/corruption.py',
    'malwarous/external_pipeline.py', 'malwarous/external_sportec.py',
    'malwarous/features.py', 'malwarous/temporal.py', 'malwarous/v2/model.py',
    'malwarous/v2/study.py', 'requirements.lock', 'starter/baseline.py',
}
TARGET_INPUTS = {
    'games.py', 'malwarous/inference.py', 'malwarous/metrica_ingest.py',
    'malwarous/v2/export.py', 'malwarous/v2/finalize.py',
    'malwarous/v2/safe_runner.py', 'malwarous/v2/target_worker.py',
    'workbench/demo.py', 'workbench/server.py',
}
EXTRA_FILES = {
    'malwarous/final_external_check.py', 'configs/v2_candidate.json',
    'scripts/check_workbench_browser.mjs', 'scripts/export_workbench_benchmarks.py',
    'scripts/prepare_review_source.py',
    'docs/V2_GUIDE.md', 'docs/V2_PROVENANCE.md', 'docs/V2_TECHNICAL_NOTE.md',
    'docs/experiments/V2_STUDY.md', 'docs/experiments/V2_RESULTS.md',
    'docs/experiments/V2_DATA_REVIEW.md', 'docs/experiments/V2_DIAGNOSIS.md',
    'docs/experiments/v2-results.json', 'docs/experiments/v2-benchmarks.json',
    'docs/experiments/V3_IMPLEMENTATION.md', 'docs/experiments/V3_PROPOSAL.md',
    'docs/experiments/V3_STUDY.md', 'docs/experiments/V3_RESULTS.md',
    'docs/experiments/v3-results.json', 'docs/experiments/V4_IMPLEMENTATION.md',
    'docs/experiments/V4_STUDY.md', 'docs/experiments/V4_RESULTS.md',
    'docs/experiments/v4-results.json', 'V4_RESULTS.md',
    'docs/experiments/FINAL_EXTERNAL_CHECK.md',
    'docs/experiments/final-external-results.json',
    'docs/experiments/FINAL_EXTERNAL_RESULTS.md',
}
OPTIONAL_FILES = {
    'docs/V2_TECHNICAL_NOTE.md', 'docs/experiments/V3_STUDY.md',
    'docs/experiments/V4_RESULTS.md', 'V4_RESULTS.md',
    'docs/experiments/FINAL_EXTERNAL_CHECK.md',
    'docs/experiments/final-external-results.json',
    'docs/experiments/FINAL_EXTERNAL_RESULTS.md',
}
GENERATED_FILES = {
    '.gitattributes', '.gitignore', 'README.md', 'MODEL_ATTRIBUTION.md',
    'docs/TECHNICAL_NOTE.md', 'docs/V1_TECHNICAL_NOTE.md',
}
MANIFEST = 'SOURCE_MANIFEST.json'
FORBIDDEN_PARTS = {
    '.git', '.venv', 'venv', 'env', '__pycache__', '.pytest_cache',
    'data', 'gt', 'results', 'artifacts_private', 'external_data_cache',
    'external_cache', 'models_external', 'ops', 'node_modules',
}
TEXT_SUFFIXES = {'.py', '.md', '.json', '.txt', '.in', '.ini', '.lock', '.mjs', '.js', '.html', '.css'}


def digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def safe_name(name: str) -> PurePosixPath:
    """Reject absolute, ambiguous, platform-specific and traversal paths."""
    if not isinstance(name, str) or not name or '\\' in name or ':' in name:
        raise ValueError('invalid relative source path')
    path = PurePosixPath(name)
    if path.is_absolute() or str(path) != name or any(p in ('', '.', '..') for p in name.split('/')):
        raise ValueError('invalid relative source path')
    if any(p.casefold() in FORBIDDEN_PARTS for p in path.parts):
        raise ValueError(f'forbidden source path: {name}')
    return path


def checked_file(root: Path, name: str) -> Path:
    relative = safe_name(name)
    root = root.resolve(strict=True)
    candidate = root.joinpath(*relative.parts)
    # Reject links/junctions in every component, even when they resolve in-root.
    current = root
    for part in relative.parts:
        current = current / part
        metadata = current.lstat()
        if current.is_symlink() or getattr(metadata, 'st_file_attributes', 0) & getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0x400):
            raise ValueError(f'linked source path: {name}')
    resolved = candidate.resolve(strict=True)
    if not resolved.is_relative_to(root) or not candidate.is_file():
        raise ValueError(f'source is not a regular in-root file: {name}')
    return candidate


def allowed_source(name: str, base_paths: set[str]) -> bool:
    path = safe_name(name)
    if name == MODEL:
        return True
    if 'models_private' in (p.casefold() for p in path.parts):
        return False
    if path.suffix.lower() not in TEXT_SUFFIXES and name not in {'.gitignore', '.gitattributes', 'LICENSE'}:
        return False
    if name in base_paths or name in EXTRA_FILES:
        return True
    if len(path.parts) >= 3 and path.parts[:2] in [('malwarous', 'v2'), ('malwarous', 'v3'), ('malwarous', 'v4')]:
        return path.suffix == '.py'
    if len(path.parts) == 2 and path.parts[0] == 'tests':
        return path.name.startswith('test') and path.suffix == '.py'
    if path.parts[0] == 'workbench':
        return path.suffix in {'.py', '.md'} or name == 'workbench/schema.json' or (
            len(path.parts) >= 3 and path.parts[1] == 'static' and path.suffix in {'.js', '.html', '.css'})
    return False


def source_bytes(root: Path, name: str) -> bytes:
    content = checked_file(root, name).read_bytes()
    if name != MODEL:
        content.decode('utf-8')
        if b'\x00' in content:
            raise ValueError(f'binary content in text allowlist: {name}')
    return content


def git_read(snapshot: Path, *arguments: str) -> bytes:
    return subprocess.run(['git', '-C', str(snapshot), *arguments], check=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout


def base_allowlist(snapshot: Path) -> set[str]:
    if git_read(snapshot, 'rev-parse', 'HEAD').decode().strip() != V1_HEAD:
        raise ValueError('v1 snapshot HEAD differs from approved snapshot')
    if git_read(snapshot, 'status', '--porcelain', '--untracked-files=no'):
        raise ValueError('v1 snapshot has tracked modifications')
    paths = set(git_read(snapshot, 'ls-tree', '-r', '--name-only', '-z', 'HEAD').decode('utf-8').strip('\x00').split('\x00'))
    for name in paths:
        if not allowed_source(name, paths) or name == MODEL:
            raise ValueError(f'unsafe base allowlist entry: {name}')
    return paths


def collect_sources(root: Path, base_paths: set[str]) -> set[str]:
    paths = set(base_paths) - GENERATED_FILES
    for name in sorted(EXTRA_FILES):
        if name in OPTIONAL_FILES and not (root / name).exists():
            continue
        checked_file(root, name)
        paths.add(name)
    # Only enumerate the explicitly approved code trees, never private folders.
    for folder in ['malwarous/v2', 'malwarous/v3', 'malwarous/v4', 'workbench', 'tests']:
        checked_folder = root / folder
        if checked_folder.is_symlink() or not checked_folder.is_dir():
            raise ValueError(f'invalid source directory: {folder}')
        for path in checked_folder.rglob('*'):
            name = path.relative_to(root).as_posix()
            # Caches are ignored before inspection; no private contents are read.
            if any(part.casefold() in FORBIDDEN_PARTS for part in path.relative_to(root).parts):
                continue
            if path.is_file() and allowed_source(name, base_paths):
                checked_file(root, name)
                paths.add(name)
    paths.add(MODEL)
    return paths


def verify_frozen_v2(root: Path, paths: set[str]) -> dict:
    """Read checksums/metadata only; never deserialize the fitted model."""
    config = json.loads(source_bytes(root, 'configs/v2_candidate.json'))
    if (config.get('id') != 'malwarous-v2-external-development'
            or config.get('candidate') != {'name': 'context_p10_r0', 'penalty': 10, 'radius': 0}
            or config.get('training_matches') != MATCHES
            or config.get('training_views') != ['original', 'drop40']
            or config.get('training_stride') != 5 or config.get('v1_preserved') is not True
            or config.get('model_relative_path') != MODEL
            or config.get('model_sha256') != MODEL_SHA256
            or config.get('report_sha256') != REPORT_SHA256):
        raise ValueError('frozen V2 candidate/model/training metadata differs')
    report_bytes = source_bytes(root, 'docs/experiments/v2-results.json')
    if digest(report_bytes) != REPORT_SHA256:
        raise ValueError('frozen V2 report checksum differs')
    report = json.loads(report_bytes)
    if (report['summary']['development_gate_passed'] is not True
            or report['summary']['selected'] != config['candidate']['name']
            or report['study']['protocol']['folds'] != [MATCHES[0:2], MATCHES[2:4], MATCHES[4:6]]
            or config['candidate'] not in report['study']['protocol']['candidates']
            or report['study']['source_sha256'] != config['study_source_sha256']):
        raise ValueError('frozen V2 study/report/config consistency differs')
    for key, expected in [('study_source_sha256', STUDY_INPUTS), ('target_source_sha256', TARGET_INPUTS)]:
        hashes = config[key]
        if set(hashes) != expected or not expected <= paths:
            raise ValueError('frozen V2 source inventory incomplete')
        for name, checksum in hashes.items():
            if digest(source_bytes(root, name)) != checksum:
                raise ValueError(f'frozen V2 source checksum differs: {name}')
    if digest(source_bytes(root, MODEL)) != MODEL_SHA256:
        raise ValueError('frozen external-only model checksum differs')
    return config


def review_ignore(snapshot_ignore: bytes) -> bytes:
    text = snapshot_ignore.decode('utf-8')
    if '*.joblib' not in text.splitlines() or '/models_private/' not in text.splitlines():
        raise ValueError('v1 safe ignore policy lacks expected model exclusions')
    return snapshot_ignore.rstrip(b'\r\n') + b'''\n\n# One frozen external-only model is included after checksum/provenance review.\n# Keep all other fitted artifacts, target outputs, caches and private material ignored.\n!/models_private/\n/models_private/*\n!/models_private/v2-possession.joblib\n'''


README = r'''# Malwarous V2 source review

The current candidate is `context_p10_r0`: contextual alive/team heads with offline
half-wise persistent decoding. Across 18 consumed-source grouped development rows,
mean spellF1 is **0.48095 versus 0.25548** for the preserved V1 smooth50 fallback;
macroF1 is **0.86868 versus 0.39809**. These are selection-conditioned development
comparisons on six previously consumed external matches, not target or blind-test
scores. V3 and V4 experiments did not replace the frozen V2 candidate.

This local review folder contains source, dependencies, external benchmark reports
and one checksum-checked external-only fitted model. It contains no Git history,
competition assets, target CSVs, private logs or viewer bundles. See
[the V2 guide](docs/V2_GUIDE.md), [provenance](docs/V2_PROVENANCE.md),
[technical note](docs/TECHNICAL_NOTE.md) and [model credit](MODEL_ATTRIBUTION.md).
The earlier fallback explanation remains in [V1 technical note](docs/V1_TECHNICAL_NOTE.md)
and [V1 provenance](docs/PROVENANCE.md); its source/config locks are preserved.

## Environment and synthetic tests

Tested with 64-bit CPython 3.11.9 and the pinned `requirements.lock`. From a working
copy of this folder in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock
.\.venv\Scripts\python.exe -m pip install -r requirements-test.in
.\.venv\Scripts\python.exe -m pytest -q
```

The tests use synthetic fixtures and public external metadata. The workbench starts
with a synthetic software demonstration when no bundle is supplied:

```powershell
.\.venv\Scripts\python.exe -m workbench.server --port 8765
```

## Reproduce V2 locally with authorized competition assets

Use a separate working copy to keep this delivery folder unchanged. Obtain the
organizer's bundle under its accepted terms. The included
`models_private/v2-possession.joblib` is the frozen all-six-external-match model;
**no training or finalizer command is needed**. `malwarous.v2.finalize` deliberately
refuses an existing config/model, so it is not a fresh-copy setup step. The runner
verifies source/report/model locks before opening target observables.

```powershell
$env:MTAH_DATA_DIR = 'D:\path\to\authorized\mtah2027-bundle'
.\.venv\Scripts\python.exe -m malwarous.v2.safe_runner v2_target_infer
.\.venv\Scripts\python.exe -m malwarous.v2.safe_runner v2_target_reproduce
```

Check the first command succeeds before running the second. The first writes
`artifacts_private/v2/Malwarous-v2.csv`; the second regenerates it and checks byte
identity. Both return status checks only and retain child diagnostics in ignored
`artifacts_private/runs/`. They do not compute a target score. Do not copy generated
target outputs or private viewer material into the review folder.

The optional local inspection command is
`.\.venv\Scripts\python.exe -m malwarous.v2.safe_runner v2_local_viewer_export`.
It creates restricted local viewer files under `artifacts_private/v2/`, with empty
truth and benchmark arrays. They remain local. External fold-study reproduction
additionally requires the separately acquired licensed source and caches described
in the V2 guide; those inputs and fold models are not bundled.

## Source integrity and licences

`SOURCE_MANIFEST.json` lists every other delivered file's SHA256 and classification;
the manifest cannot hash itself. The model's expected SHA256 is
`c6deb427e42dca2b2d35ffa47576f4fbb94509729c0216b46312b1f367c2418d`.
`.gitattributes` uses `* -text` to preserve the mixed LF/CRLF raw bytes covered by
the frozen source locks if a repository is initialized later. No such initialization,
commit, upload or publication is performed by the preparation tool.

Code retains the MIT notice in [LICENSE](LICENSE), including the organizer source
at `f8f2629ff1e0985f81d7e59d8413678514ee1530`. The external model credit and CC BY 4.0
terms are in [MODEL_ATTRIBUTION.md](MODEL_ATTRIBUTION.md). Competition assets have
separate restricted terms and are excluded.
'''

MODEL_CREDIT = '''# Frozen external-only model credit

`models_private/v2-possession.joblib` is the one approved fitted artifact in this
source review. SHA256:
`c6deb427e42dca2b2d35ffa47576f4fbb94509729c0216b46312b1f367c2418d`.
It was fitted on J03WN1, J03WOY, J03WPY, J03WOH, J03WQQ and J03WR9 only, using
original and synthetic drop40 views at stride 5. J03WMX is excluded. No competition
target data or target labels were used in fitting. It contains fitted parameters;
no raw source tracking or label arrays are distributed here.

Source credit: Manuel Bassek, Robert Rein, Hendrik Weber and Daniel Memmert,
“An integrated dataset of spatiotemporal and event data in elite soccer.”
[Dataset, version 1](https://doi.org/10.6084/m9.figshare.28196177.v1),
[Scientific Data paper](https://doi.org/10.1038/s41597-025-04505-y), licensed under
[Creative Commons Attribution 4.0 International](https://creativecommons.org/licenses/by/4.0/).
The fitted model, derived benchmark results, coordinate/feature transformations and
synthetic dropout are Malwarous modifications of the licensed source. This credit
and the CC BY 4.0 licence link must accompany redistribution of the derived model.
No endorsement by the dataset authors is implied. Repository code remains under MIT.
'''


def generated_content(root: Path, snapshot: Path) -> dict[str, bytes]:
    current_note = ('docs/V2_TECHNICAL_NOTE.md' if (root / 'docs/V2_TECHNICAL_NOTE.md').exists() else None)
    note = (source_bytes(root, current_note) if current_note else
            b'# Malwarous V2 technical method\n\nSee [V2 guide](V2_GUIDE.md) and '
            b'[V2 provenance](V2_PROVENANCE.md) for the current frozen candidate.\n'
            b'The preserved fallback description is [V1 technical note](V1_TECHNICAL_NOTE.md).\n')
    return {
        '.gitattributes': b'# Preserve the raw bytes covered by frozen V1/V2 locks.\n* -text\n',
        '.gitignore': review_ignore(source_bytes(snapshot, '.gitignore')),
        'README.md': README.encode('utf-8'),
        'MODEL_ATTRIBUTION.md': MODEL_CREDIT.encode('utf-8'),
        'docs/TECHNICAL_NOTE.md': note,
        'docs/V1_TECHNICAL_NOTE.md': source_bytes(root, 'docs/TECHNICAL_NOTE.md'),
    }


def validate_destination(destination: Path, root: Path, snapshot: Path | None = None) -> None:
    destination = destination.absolute()
    resolved = destination.resolve()
    for protected in [root] + ([snapshot] if snapshot is not None else []):
        protected = protected.resolve(strict=True)
        if resolved == protected or resolved.is_relative_to(protected) or protected.is_relative_to(resolved):
            raise ValueError('destination overlaps a protected source tree')
    for parent in [destination, *destination.parents]:
        if parent.exists():
            metadata = parent.lstat()
            if parent.is_symlink() or getattr(metadata, 'st_file_attributes', 0) & getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0x400):
                raise ValueError('linked destination path')
    if destination.exists() and (not destination.is_dir() or any(destination.iterdir())):
        raise FileExistsError('destination must be absent or empty; no existing files are replaced')


def write_bundle(root: Path, destination: Path, paths: set[str], base_paths: set[str],
                 generated: dict[str, bytes], *, model_sha256: str = MODEL_SHA256) -> dict:
    """Preflight every byte before creating files; exclusively create each output."""
    validate_destination(destination, root)
    if set(generated) - GENERATED_FILES:
        raise ValueError('unapproved generated file')
    contents = {}
    for name in sorted(paths):
        if not allowed_source(name, base_paths):
            raise ValueError(f'non-allowlisted source: {name}')
        content = source_bytes(root, name)
        if name == MODEL and digest(content) != model_sha256:
            raise ValueError('external model checksum differs')
        contents[name] = (content, 'external_only_frozen_model' if name == MODEL else 'source_or_external_report')
    for name, content in generated.items():
        safe_name(name)
        content.decode('utf-8')
        contents[name] = (content, 'generated_review_document')
    manifest = {
        'schema': 1, 'purpose': 'local source review; no Git history or publication',
        'base_allowlist_commit': V1_HEAD,
        'model_sha256': model_sha256,
        'excluded_self': MANIFEST,
        'files': [{'path': name, 'sha256': digest(content), 'bytes': len(content),
                   'classification': classification}
                  for name, (content, classification) in sorted(contents.items())],
    }
    # Recheck immediately before the first write; never merge with an existing tree.
    validate_destination(destination, root)
    destination.mkdir(parents=True, exist_ok=True)
    for name, (content, _) in sorted(contents.items()):
        output = destination.joinpath(*safe_name(name).parts)
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open('xb') as stream:
            stream.write(content)
    with (destination / MANIFEST).open('xb') as stream:
        stream.write((json.dumps(manifest, indent=2, sort_keys=True) + '\n').encode('utf-8'))
    verify_bundle(destination)
    return manifest


def verify_bundle(destination: Path) -> dict:
    manifest = json.loads(checked_file(destination, MANIFEST).read_bytes())
    expected = {entry['path'] for entry in manifest['files']}
    if len(expected) != len(manifest['files']) or MANIFEST in expected or manifest['excluded_self'] != MANIFEST:
        raise ValueError('invalid manifest inventory')
    actual = {path.relative_to(destination).as_posix() for path in destination.rglob('*') if path.is_file()}
    if actual != expected | {MANIFEST}:
        raise ValueError('review folder inventory differs from manifest')
    for entry in manifest['files']:
        content = source_bytes(destination, entry['path'])
        if digest(content) != entry['sha256'] or len(content) != entry['bytes']:
            raise ValueError(f'review folder checksum differs: {entry["path"]}')
        if entry['path'] == MODEL and digest(content) != manifest['model_sha256']:
            raise ValueError('review model checksum differs')
    return manifest


def prepare(root: Path, snapshot: Path, destination: Path) -> dict:
    root, snapshot = root.resolve(strict=True), snapshot.resolve(strict=True)
    validate_destination(destination, root, snapshot)
    base_paths = base_allowlist(snapshot)
    paths = collect_sources(root, base_paths)
    verify_frozen_v2(root, paths)
    generated = generated_content(root, snapshot)
    # Recheck snapshot state without mutating it, after all read-only preflight.
    if base_allowlist(snapshot) != base_paths:
        raise ValueError('base snapshot changed during preflight')
    result = write_bundle(root, destination, paths, base_paths, generated)
    verify_frozen_v2(destination, set(entry['path'] for entry in result['files']))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--v1-snapshot', type=Path,
                        default=Path(__file__).resolve().parents[2] / 'submission_review' / 'Malwarous-public')
    parser.add_argument('--destination', type=Path,
                        default=Path(__file__).resolve().parents[2] / 'submission_review' / 'Malwarous-v2-source')
    parser.add_argument('--verify-only', action='store_true')
    args = parser.parse_args()
    manifest = verify_bundle(args.destination) if args.verify_only else prepare(args.repo, args.v1_snapshot, args.destination)
    print(json.dumps({'status': 'verified' if args.verify_only else 'prepared',
                      'files': len(manifest['files']) + 1,
                      'manifest': str(args.destination / MANIFEST)}, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
