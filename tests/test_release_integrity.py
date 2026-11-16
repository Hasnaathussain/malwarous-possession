"""Synthetic path and file guards for the small release-integrity module."""
from pathlib import Path

import pytest

from scripts import release_integrity as release


@pytest.mark.parametrize('name', [
    '../outside.py', '/absolute.py', 'C:/outside.py', 'C:relative.py',
    'folder//file.py', 'folder/./file.py', r'folder\file.py',
    '.git/config', 'data/secret.json', 'artifacts_private/run.json',
    'external_data_cache/match.xml', 'docs/ops/state.md',
])
def test_unsafe_or_private_inventory_paths_are_rejected(name):
    with pytest.raises(ValueError):
        release.safe_name(name)


def test_source_bytes_require_utf8_and_reject_nul(tmp_path):
    path = tmp_path / 'example.py'
    path.write_bytes(b'# valid synthetic source\n')
    assert release.source_bytes(tmp_path, 'example.py') == path.read_bytes()
    path.write_bytes(b'# source\x00payload')
    with pytest.raises(ValueError, match='binary content'):
        release.source_bytes(tmp_path, 'example.py')
    path.write_bytes(b'\xff\xfe')
    with pytest.raises(UnicodeDecodeError):
        release.source_bytes(tmp_path, 'example.py')


def test_only_the_named_external_model_has_a_binary_read_exception(tmp_path):
    model = tmp_path / release.MODEL
    model.parent.mkdir()
    model.write_bytes(b'\xff\x00synthetic fixture, never unpickled')
    assert release.source_bytes(tmp_path, release.MODEL) == model.read_bytes()
    other = model.with_name('other.joblib')
    other.write_bytes(model.read_bytes())
    with pytest.raises(UnicodeDecodeError):
        release.source_bytes(tmp_path, 'models_private/other.joblib')


def test_linked_file_is_rejected_before_reading(tmp_path, monkeypatch):
    path = tmp_path / 'example.py'
    path.write_text('# fixture', encoding='utf-8')
    original = Path.is_symlink
    monkeypatch.setattr(Path, 'is_symlink', lambda self: self == path or original(self))
    with pytest.raises(ValueError, match='linked source path'):
        release.checked_file(tmp_path, 'example.py')
