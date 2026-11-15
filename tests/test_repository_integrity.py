"""Repository inventory guards on temporary synthetic fixtures, never target data."""
import hashlib
import json
from pathlib import Path
import subprocess

import pytest
from scripts import verify_repository as integrity


def fixture(tmp_path, monkeypatch):
    code = tmp_path / 'example.py'
    code.write_bytes(b'# synthetic source\n')
    (tmp_path / 'SOURCE_MANIFEST.json').write_text(json.dumps({
        'excluded_self': 'SOURCE_MANIFEST.json',
        'files': [{'path': 'example.py', 'bytes': code.stat().st_size,
                   'sha256': hashlib.sha256(code.read_bytes()).hexdigest()}]}), encoding='utf-8')
    monkeypatch.setattr(integrity.review, 'verify_frozen_v2', lambda *args: None)
    return code


def git(root, *args):
    return subprocess.run(['git', '-C', str(root), *args], check=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def test_plain_delivery_verifies(tmp_path, monkeypatch):
    fixture(tmp_path, monkeypatch)
    assert integrity.verify(tmp_path)['status'] == 'verified'


def test_git_metadata_and_ignored_local_files_do_not_break_verification(tmp_path, monkeypatch):
    fixture(tmp_path, monkeypatch)
    git(tmp_path, 'init', '-q')
    git(tmp_path, '-c', 'core.autocrlf=false', 'add', '--', 'example.py', 'SOURCE_MANIFEST.json')
    (tmp_path / 'artifacts_private').mkdir()
    (tmp_path / 'artifacts_private' / 'synthetic-local.txt').write_text('not committed', encoding='utf-8')
    assert integrity.verify(tmp_path)['source_files'] == 2


def test_accidentally_staged_extra_file_is_rejected(tmp_path, monkeypatch):
    fixture(tmp_path, monkeypatch)
    git(tmp_path, 'init', '-q')
    git(tmp_path, '-c', 'core.autocrlf=false', 'add', '--', 'example.py', 'SOURCE_MANIFEST.json')
    (tmp_path / 'unexpected.txt').write_text('synthetic extra', encoding='utf-8')
    git(tmp_path, 'add', '--', 'unexpected.txt')
    with pytest.raises(ValueError, match='inventory differs'):
        integrity.verify(tmp_path)


def test_changed_frozen_source_bytes_are_rejected(tmp_path, monkeypatch):
    code = fixture(tmp_path, monkeypatch)
    code.write_bytes(b'# altered after review\n')
    with pytest.raises(ValueError, match='checksum differs'):
        integrity.verify(tmp_path)


def test_duplicate_manifest_entry_is_rejected(tmp_path, monkeypatch):
    fixture(tmp_path, monkeypatch)
    path = tmp_path / 'SOURCE_MANIFEST.json'
    manifest = json.loads(path.read_text('utf-8'))
    manifest['files'] *= 2
    path.write_text(json.dumps(manifest), encoding='utf-8')
    with pytest.raises(ValueError, match='invalid source inventory'):
        integrity.verify(tmp_path)


def test_stale_staged_bytes_are_rejected_even_when_working_manifest_matches(tmp_path, monkeypatch):
    code = fixture(tmp_path, monkeypatch)
    git(tmp_path, 'init', '-q')
    git(tmp_path, '-c', 'core.autocrlf=false', 'add', '--', 'example.py', 'SOURCE_MANIFEST.json')
    code.write_bytes(b'# updated synthetic source\n')
    path = tmp_path / 'SOURCE_MANIFEST.json'
    manifest = json.loads(path.read_text('utf-8'))
    manifest['files'][0].update(bytes=code.stat().st_size,
        sha256=hashlib.sha256(code.read_bytes()).hexdigest())
    path.write_text(json.dumps(manifest), encoding='utf-8')
    with pytest.raises(ValueError, match='staged bytes differ'):
        integrity.verify(tmp_path)
