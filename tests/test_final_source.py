"""The final edition keeps frozen dependencies and excludes inactive experiments."""
from pathlib import Path

import pytest

from scripts import prepare_final_source as final
from scripts import prepare_review_source as review
from malwarous.private_worker import RELEASE_RUNNER_INPUTS, SELECTION_CODE_INPUTS


def test_frozen_runtime_dependencies_are_retained():
    assert set(RELEASE_RUNNER_INPUTS) <= final.CORE
    assert set(SELECTION_CODE_INPUTS) <= final.CORE
    assert review.STUDY_INPUTS - {'malwarous/v2/model.py', 'malwarous/v2/study.py'} <= final.CORE
    assert review.TARGET_INPUTS - {
        'malwarous/v2/export.py', 'malwarous/v2/finalize.py',
        'malwarous/v2/safe_runner.py', 'malwarous/v2/target_worker.py',
        'workbench/demo.py', 'workbench/server.py',
    } <= final.CORE


def test_default_test_discovery_ignores_private_verification_copies():
    import configparser
    parser = configparser.ConfigParser()
    parser.read(Path(__file__).resolve().parents[1] / 'pytest.ini')
    assert parser['pytest']['testpaths'].split() == ['tests']
    assert 'artifacts_private' in parser['pytest']['norecursedirs'].split()


def test_inactive_experiments_and_private_work_are_not_inventory_inputs():
    assert not any('/v3/' in p or '/v4/' in p or '/v5/' in p for p in final.CORE)
    assert set(final.TREES) == {'malwarous/v2', 'workbench'}
    assert not any('private' in p for p in final.CORE if p != review.MODEL and p != 'malwarous/private_worker.py')
    assert all('test_v3' not in p and 'test_v4' not in p for p in final.TESTS)


def test_nonempty_destination_cannot_be_overwritten(tmp_path):
    source = tmp_path / 'research'
    source.mkdir()
    destination = tmp_path / 'edition'
    destination.mkdir()
    existing = destination / 'valuable.txt'
    existing.write_text('do not replace', encoding='utf-8')
    with pytest.raises(FileExistsError):
        final.prepare(source, destination)
    assert existing.read_text('utf-8') == 'do not replace'


def test_final_ignore_admits_only_the_named_external_weights(tmp_path):
    import subprocess
    (tmp_path / '.gitignore').write_text(final.IGNORE, encoding='utf-8')
    subprocess.run(['git', 'init', '-q', str(tmp_path)], check=True)
    for name in ['other.joblib', 'models_private/other.joblib', 'private.csv',
                 'artifacts_private/viewer.json', 'data/secret.json', '.env', '.pytest_cache/test']:
        p = subprocess.run(['git', '-C', str(tmp_path), 'check-ignore', '-q', name])
        assert p.returncode == 0, name
    p = subprocess.run(['git', '-C', str(tmp_path), 'check-ignore', '-q', review.MODEL])
    assert p.returncode == 1
