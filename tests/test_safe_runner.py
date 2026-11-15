"""Synthetic-only checks that private child output never reaches runner results."""

import json
from pathlib import Path
import sys
import tempfile
import unittest

from malwarous.safe_runner import _launch, run


class SafeRunnerTests(unittest.TestCase):
    def run_child(self, source: str, timeout: int = 5):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        base = Path(temp.name)
        status = base / "status.json"
        log = base / "private.log"
        command = [sys.executable, "-c", source, str(status)]
        result = _launch("synthetic_probe", command, status, log, timeout)
        return result, log.read_text(encoding="utf-8", errors="replace")

    def test_child_stdout_stderr_and_exception_text_stay_private(self):
        sentinels = ["TRACK_SECRET", "ANNOTATION_SECRET", "WARNING_SECRET", "PATH_SECRET"]
        child = "\n".join([
            "import json, sys, warnings",
            "p=sys.argv[1]",
            "print('TRACK_SECRET')",
            "print('ANNOTATION_SECRET', file=sys.stderr)",
            "warnings.warn('WARNING_SECRET at /private/PATH_SECRET')",
            "open(p, 'w').write(json.dumps({'job':'synthetic_probe','status':'completed','checks':{'frame_contract':'pass'}}))",
        ])
        result, private_log = self.run_child(child)
        returned = json.dumps(result)
        self.assertEqual(result["status"], "completed")
        for secret in sentinels:
            self.assertNotIn(secret, returned)
            self.assertIn(secret, private_log)

    def test_malformed_status_is_generic(self):
        child = "import sys; open(sys.argv[1], 'w').write('bad SECRET')"
        result, private_log = self.run_child(child)
        self.assertEqual(result["failure_code"], "INTERNAL_ERROR")
        self.assertNotIn("SECRET", json.dumps(result))
        self.assertEqual(private_log, "")

    def test_crash_does_not_return_exception_details(self):
        child = "raise RuntimeError('EXCEPTION_SECRET')"
        result, private_log = self.run_child(child)
        self.assertEqual(result["status"], "failed")
        self.assertNotIn("EXCEPTION_SECRET", json.dumps(result))
        self.assertIn("EXCEPTION_SECRET", private_log)

    def test_timeout_is_generic(self):
        child = "import time; time.sleep(5)"
        result, _ = self.run_child(child, timeout=1)
        self.assertEqual(result["failure_code"], "RESOURCE_LIMIT")
        self.assertNotIn("Traceback", json.dumps(result))

    def test_worker_cannot_return_unapproved_fields(self):
        child = "import json, sys; open(sys.argv[1], 'w').write(json.dumps({'job':'synthetic_probe','status':'completed','checks':{'frame_contract':'pass'},'raw':'LEAK_SECRET'}))"
        result, _ = self.run_child(child)
        self.assertEqual(set(result), {"job", "status", "checks", "details"})
        self.assertNotIn("LEAK_SECRET", json.dumps(result))

    def test_production_bootstrap_blocks_python_socket_before_worker_execution(self):
        result = run("runner_self_test", timeout_seconds=10)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["checks"], {"offline_guard": "pass"})

    def test_unknown_production_job_is_rejected_before_launch(self):
        with self.assertRaises(ValueError):
            run("arbitrary_command")

    def test_unhashable_status_fields_are_generic(self):
        for field, value in (("status", []), ("failure_code", {}), ("checks", {"frame_contract": []})):
            with self.subTest(field=field):
                child = (
                    "import json, sys; d={'job':'synthetic_probe','status':'completed','checks':{}}; "
                    f"d[{field!r}]={value!r}; open(sys.argv[1],'w').write(json.dumps(d))"
                )
                result, _ = self.run_child(child)
                self.assertEqual(result["failure_code"], "INTERNAL_ERROR")


if __name__ == "__main__":
    unittest.main()
