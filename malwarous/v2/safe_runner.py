"""V2 entry point using the existing reviewed status-only child/log boundary."""
from __future__ import annotations
import argparse
import json
import os
import sys
import uuid
from malwarous.safe_runner import ROOT, _private_root, _launch, _status

JOBS = ('v2_target_infer', 'v2_target_reproduce', 'v2_local_viewer_export')


def run(job, timeout=21600):
    if job not in JOBS or not 1 <= timeout <= 21600:
        raise ValueError('unsupported fixed v2 job/timeout')
    folder = _private_root()
    identity = 'v2-' + uuid.uuid4().hex
    status = folder / (identity + '.status.json')
    log = folder / (identity + '.log')
    # Import SSL before blocking sockets: its socket subclass must be constructed
    # normally, but the module does not open a network connection on import.
    bootstrap = (
        "import os,runpy,socket,ssl,sys; "
        "sys.path.insert(0,sys.argv[1]); "
        "blocked=lambda *a,**k: (_ for _ in ()).throw(OSError('network disabled')); "
        "socket.socket=blocked;socket.create_connection=blocked;socket.getaddrinfo=blocked; "
        "os.environ['MALWAROUS_V2_SAFE_RUNNER']='1'; "
        "sys.argv=['malwarous.v2.target_worker',sys.argv[2],sys.argv[3]]; "
        "runpy.run_module('malwarous.v2.target_worker',run_name='__main__')"
    )
    command = [sys.executable, '-s', '-c', bootstrap, str(ROOT), job, str(status)]
    return _launch(job, command, status, log, timeout)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('job', choices=JOBS)
    parser.add_argument('--timeout', type=int, default=21600)
    args = parser.parse_args()
    try:
        result = run(args.job, args.timeout)
    except Exception:
        result = _status(args.job, 'failed', failure_code='INTERNAL_ERROR')
    print(json.dumps(result, sort_keys=True))
    return 0 if result['status'] == 'completed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
