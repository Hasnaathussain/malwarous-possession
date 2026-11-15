"""Actual guarded child import/decoding, using only synthetic observations."""
import json
from pathlib import Path
import sys

from malwarous.safe_runner import ROOT, _launch


def test_v2_model_can_execute_inside_status_only_offline_child(tmp_path):
    status = tmp_path / 'synthetic.status.json'
    log = tmp_path / 'synthetic.log'
    code = '''
import json, socket, ssl, sys
sys.path.insert(0, sys.argv[1])
def blocked(*args, **kwargs):
    raise OSError('synthetic offline boundary')
socket.socket = blocked
socket.create_connection = blocked
socket.getaddrinfo = blocked
import numpy as np
from malwarous.v2.model import build_context, decode
players = np.zeros((50, 2, 2), dtype=np.float32)
players[:, 1, 0] = 8
ball = np.zeros((50, 2), dtype=np.float32)
ball[10:20] = np.nan
context = build_context(players, [0, 1], ball)
assert np.isfinite(context.original).all()
evidence = np.log(np.tile([.8, .1, .1], (50, 1)))
assert np.array_equal(decode(evidence, 25), np.zeros(50))
with open(sys.argv[2], 'w') as f:
    json.dump({'job':'runner_self_test','status':'completed',
               'checks':{'offline_guard':'pass','finite_evidence':'pass'}}, f)
'''
    result = _launch('runner_self_test', [sys.executable, '-s', '-c', code, str(ROOT), str(status)],
                     status, log, timeout_seconds=180)
    assert result['status'] == 'completed'
    assert result['checks'] == {'offline_guard': 'pass', 'finite_evidence': 'pass'}
    assert result['details'] == 'retained_locally'
    assert not any(key in result for key in ('stdout', 'stderr', 'log'))
