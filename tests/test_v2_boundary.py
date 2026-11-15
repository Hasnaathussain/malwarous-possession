"""Synthetic v2 launch, alignment and local-export boundaries; no match assets."""
from __future__ import annotations

import json
import hashlib
from pathlib import Path
import socket
import sys
from types import SimpleNamespace

import numpy as np
import pytest
import joblib

import games
from malwarous import metrica_ingest
from malwarous.v2 import model, safe_runner, target_worker


def _fail_if_called(*args, **kwargs):
    raise AssertionError('target access must not occur')


def _blocked_socket(*args, **kwargs):
    raise OSError('synthetic offline guard')


def test_runner_rejects_unknown_jobs_and_invalid_timeouts_before_launch(monkeypatch):
    monkeypatch.setattr(safe_runner, '_private_root', _fail_if_called)
    for job, timeout in [('arbitrary', 1), ('v2_target_infer', 0),
                         ('v2_target_infer', 21601)]:
        with pytest.raises(ValueError):
            safe_runner.run(job, timeout)


def test_worker_refuses_missing_launch_marker_or_live_socket(monkeypatch):
    monkeypatch.setattr(target_worker, 'generate', _fail_if_called)
    monkeypatch.delenv('MALWAROUS_V2_SAFE_RUNNER', raising=False)
    assert target_worker.main() == 2
    monkeypatch.setenv('MALWAROUS_V2_SAFE_RUNNER', '1')
    # Fake a successful socket constructor without opening any socket.
    monkeypatch.setattr(socket, 'socket', lambda: object())
    assert target_worker.main() == 2


def test_worker_refuses_status_path_outside_private_runs(monkeypatch, tmp_path):
    monkeypatch.setenv('MALWAROUS_V2_SAFE_RUNNER', '1')
    monkeypatch.setattr(socket, 'socket', _blocked_socket)
    monkeypatch.setattr(target_worker, 'ROOT', tmp_path)
    monkeypatch.setattr(target_worker, 'generate', _fail_if_called)
    status = tmp_path / 'v2-outside.json'
    monkeypatch.setattr(sys, 'argv', ['worker', 'v2_target_infer', str(status)])
    assert target_worker.main() == 2
    assert not status.exists()


def test_failed_model_gate_precedes_target_existence_or_content_access(monkeypatch):
    monkeypatch.setenv('MALWAROUS_V2_SAFE_RUNNER', '1')
    monkeypatch.setattr(socket, 'socket', _blocked_socket)
    def reject():
        raise ValueError('synthetic rejected source gate')
    monkeypatch.setattr(target_worker, 'locked_model', reject)
    monkeypatch.setattr(games, 'require', _fail_if_called)
    monkeypatch.setattr(games, 'asset_paths', _fail_if_called)
    monkeypatch.setattr(metrica_ingest, 'team_slots_from_metadata', _fail_if_called)
    monkeypatch.setattr(metrica_ingest, 'load_metrica_tracking', _fail_if_called)
    with pytest.raises(ValueError, match='synthetic rejected source gate'):
        target_worker.generate()


@pytest.mark.parametrize('tamper', ['source', 'report', 'candidate', 'model'])
def test_locked_model_rejects_tampered_inputs_before_unpickling(monkeypatch, tmp_path, tamper):
    from malwarous import private_worker
    monkeypatch.setenv('MALWAROUS_V2_SAFE_RUNNER', '1')
    monkeypatch.setattr(socket, 'socket', _blocked_socket)
    monkeypatch.setattr(target_worker, 'ROOT', tmp_path)
    monkeypatch.setattr(private_worker, '_locked_window', lambda: 50)
    monkeypatch.setattr(joblib, 'load', _fail_if_called)
    digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    target_hashes = {}
    for name in target_worker.TARGET_INPUTS:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('# synthetic locked source\n')
        target_hashes[name] = digest(path)
    model_source = tmp_path / 'malwarous/v2/model.py'
    model_source.write_text('# synthetic model source\n')
    candidate = {'name': 'synthetic', 'penalty': 25, 'radius': 12}
    report = {'summary': {'development_gate_passed': True, 'selected': 'synthetic'},
              'study': {'protocol': {'candidates': [candidate]}}}
    report_path = tmp_path / 'docs/experiments/v2-results.json'
    report_path.parent.mkdir(parents=True)
    report_path.write_text(json.dumps(report))
    model_path = tmp_path / 'models_private/v2-possession.joblib'
    model_path.parent.mkdir()
    model_path.write_bytes(b'synthetic non-pickle bytes')
    manifest = {'id': 'malwarous-v2-external-development', 'candidate': dict(candidate),
        'target_source_sha256': target_hashes,
        'study_source_sha256': {'malwarous/v2/model.py': digest(model_source)},
        'report_sha256': digest(report_path),
        'model_relative_path': 'models_private/v2-possession.joblib',
        'model_sha256': digest(model_path)}
    if tamper == 'source':
        model_source.write_text('# changed synthetic source\n')
    elif tamper == 'report':
        report_path.write_text(json.dumps(report) + '\n')
    elif tamper == 'candidate':
        manifest['candidate']['penalty'] = 99
    else:
        model_path.write_bytes(b'changed synthetic bytes')
    manifest_path = tmp_path / 'configs/v2_candidate.json'
    manifest_path.parent.mkdir()
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError):
        target_worker.locked_model()


def test_generation_centres_coordinates_and_resets_at_official_half_boundaries(monkeypatch):
    monkeypatch.setenv('MALWAROUS_V2_SAFE_RUNNER', '1')
    monkeypatch.setattr(socket, 'socket', _blocked_socket)
    n = 199319
    pitch = games.GAMES[games.GAME]['pitch']
    centre = np.asarray(pitch, dtype=np.float32) / 2
    players = np.broadcast_to(centre, (n, 2, 2)).copy()
    ball = np.broadcast_to(centre, (n, 2)).copy()
    tracking = SimpleNamespace(player_xy=players, ball_xy=ball,
                               team_by_slot=np.array([0, 1]))
    expected = games.half_video_blocks(games.GAME)
    manifest = {'candidate': {'penalty': 25, 'radius': 12}}
    monkeypatch.setattr(target_worker, 'locked_model', lambda: (manifest, object()))
    monkeypatch.setattr(games, 'require', lambda *a, **k: None)
    monkeypatch.setattr(games, 'asset_paths', lambda: {'atd_raw': 'synthetic', 'atd_meta': 'synthetic'})
    monkeypatch.setattr(metrica_ingest, 'team_slots_from_metadata', lambda p: tracking.team_by_slot)
    monkeypatch.setattr(metrica_ingest, 'load_metrica_tracking', lambda *a, **k: tracking)
    lengths = []
    def context(p, teams, b, **kwargs):
        np.testing.assert_array_equal(p, 0)
        np.testing.assert_array_equal(b, 0)
        assert kwargs == {'pitch': pitch, 'fps': 25.}
        lengths.append(len(b))
        return SimpleNamespace(n=len(b))
    monkeypatch.setattr(model, 'build_context', context)
    monkeypatch.setattr(model, 'emissions', lambda m, c: np.zeros((c.n, 3), dtype=np.float32))
    monkeypatch.setattr(model, 'decode', lambda s, p, r: np.zeros(len(s), dtype=np.int8))
    labels, evidence, _, views, _ = target_worker.generate()
    assert lengths == [last - start + 1 for _, start, last in expected]
    inside = np.zeros(n, dtype=bool)
    for _, start, last in expected:
        inside[start:last + 1] = True
    assert np.all(labels[inside] == 0)
    assert np.all(labels[~inside] == 3)
    assert np.isfinite(evidence[inside]).all()
    assert np.isnan(evidence[~inside]).all()
    assert [(start, stop) for start, stop, _ in views] == [(s, e + 1) for _, s, e in expected]


def _worker_fixture(monkeypatch, tmp_path, job):
    monkeypatch.setenv('MALWAROUS_V2_SAFE_RUNNER', '1')
    monkeypatch.setattr(socket, 'socket', _blocked_socket)
    monkeypatch.setattr(target_worker, 'ROOT', tmp_path)
    monkeypatch.setattr(target_worker, 'PRIVATE', tmp_path / 'private-v2')
    labels = np.arange(199319, dtype=np.int32) % 4
    monkeypatch.setattr(target_worker, 'generate', lambda: (labels, None, None, None, None))
    run_dir = tmp_path / 'artifacts_private' / 'runs'
    run_dir.mkdir(parents=True, exist_ok=True)
    status = run_dir / 'v2-synthetic.status.json'
    monkeypatch.setattr(sys, 'argv', ['worker', job, str(status)])
    return status


def test_canonical_csv_and_byte_reproduction_use_only_synthetic_labels(monkeypatch, tmp_path):
    status = _worker_fixture(monkeypatch, tmp_path, 'v2_target_infer')
    assert target_worker.main() == 0
    result = json.loads(status.read_text())
    assert result['checks']['csv_contract'] == 'pass'
    output = target_worker.PRIVATE / 'Malwarous-v2.csv'
    original = output.read_bytes()
    assert original.startswith(b'frame,label\n0,H\n1,A\n2,D\n3,X\n')
    assert len(original.splitlines()) == 199320
    assert b'\r' not in original
    monkeypatch.setattr(sys, 'argv', ['worker', 'v2_target_reproduce', str(status)])
    assert target_worker.main() == 0
    assert json.loads(status.read_text())['checks']['byte_reproduction'] == 'pass'
    output.write_bytes(original.replace(b'\n', b'\r\n'))
    assert target_worker.main() == 1
    failed = json.loads(status.read_text())
    assert failed['status'] == 'failed'
    assert 'byte_reproduction' not in failed['checks']


def test_local_export_has_predictions_without_truth_metrics_or_training_labels(monkeypatch, tmp_path):
    monkeypatch.setenv('MALWAROUS_V2_SAFE_RUNNER', '1')
    monkeypatch.setattr(socket, 'socket', _blocked_socket)
    monkeypatch.setattr(target_worker, 'ROOT', tmp_path)
    monkeypatch.setattr(target_worker, 'PRIVATE', tmp_path / 'private-v2')
    monkeypatch.setattr(games, 'asset_paths', lambda: {'video': str(tmp_path / 'synthetic.mp4')})
    tracking = SimpleNamespace(ball_xy=np.array([[52.65, 34.]]),
        player_xy=np.array([[[1., 2.], [3., 4.]]]), team_by_slot=np.array([0, 1]))
    context = SimpleNamespace(original=np.array([[1.]]), names=('ball_support_4s',))
    target_worker.export_local(np.array([0, 1, 2, 3]), np.array([[2., 1., 0.]]),
        tracking, [(0, 1, context)], {'candidate': {'name': 'synthetic'}})
    bundle = json.loads((target_worker.PRIVATE / 'local-viewer' / 'bundle.json').read_text())
    assert bundle['dataset']['kind'] == 'private_local'
    match = bundle['matches'][0]
    assert match['truth'] == [] and match['benchmarks'] == []
    assert set(match['predictions']) == {'v2'}
    assert match['samples'][0]['ball'] == [52.65, 34.]
    assert match['samples'][0]['players'][0]['x'] == 1.
    assert 'confidence' not in json.dumps(bundle).replace('no invented confidence', '')


@pytest.mark.parametrize('entry', ['locked_model', 'generate', 'export_local'])
def test_direct_target_helpers_require_the_guard_before_any_access(monkeypatch, entry):
    monkeypatch.delenv('MALWAROUS_V2_SAFE_RUNNER', raising=False)
    monkeypatch.setattr(games, 'require', _fail_if_called)
    monkeypatch.setattr(games, 'asset_paths', _fail_if_called)
    monkeypatch.setattr(Path, 'read_bytes', _fail_if_called)
    monkeypatch.setattr(Path, 'read_text', _fail_if_called)
    args = (None, None, None, None, None) if entry == 'export_local' else ()
    with pytest.raises(RuntimeError):
        getattr(target_worker, entry)(*args)
