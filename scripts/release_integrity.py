"""Path safety and checksum verification for the frozen submission release."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
import stat

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

MANIFEST = 'SOURCE_MANIFEST.json'

FORBIDDEN_PARTS = {
    '.git', '.venv', 'venv', 'env', '__pycache__', '.pytest_cache',
    'data', 'gt', 'results', 'artifacts_private', 'external_data_cache',
    'external_cache', 'models_external', 'ops', 'node_modules',
}

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

def source_bytes(root: Path, name: str) -> bytes:
    content = checked_file(root, name).read_bytes()
    if name != MODEL:
        content.decode('utf-8')
        if b'\x00' in content:
            raise ValueError(f'binary content in text allowlist: {name}')
    return content

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
