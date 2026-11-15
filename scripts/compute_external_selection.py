"""Child process for the frozen public-data candidate comparison; emits one JSON result."""

from __future__ import annotations

import json
import platform
from pathlib import Path
import socket
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _network_blocked(*_args, **_kwargs):
    raise OSError("network disabled for the local external-data experiment")


from malwarous.experiments import _protocol_digest, load_protocol, run_selection  # noqa: E402
import numpy as np  # noqa: E402
import sklearn  # noqa: E402

socket.socket = _network_blocked
socket.create_connection = _network_blocked
socket.getaddrinfo = _network_blocked


def main() -> int:
    try:
        protocol = load_protocol(ROOT / "configs" / "experiment_protocol.json")
        if sys.argv[1:] == ["--preflight"]:
            print(json.dumps({
                "status": "ready",
                "protocol_sha256": _protocol_digest(protocol),
            }, sort_keys=True, separators=(",", ":")))
            return 0
        if sys.argv[1:]:
            print(json.dumps({"status": "failed", "failure_type": "InvalidArguments"}))
            return 2
        result = run_selection(protocol)
        result["runtime"] = {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "numpy": np.__version__,
            "scikit_learn": sklearn.__version__,
        }
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "failed", "failure_type": type(exc).__name__}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
