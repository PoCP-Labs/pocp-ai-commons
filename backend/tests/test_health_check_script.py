"""Regression: repository health_check.py must pass in CI and local QA."""

import subprocess
import sys
import unittest
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_SCRIPT = _REPO / "backend" / "scripts" / "health_check.py"


class HealthCheckScriptTests(unittest.TestCase):
    def test_health_check_script_exits_zero(self):
        proc = subprocess.run(
            [sys.executable, str(_SCRIPT)],
            cwd=str(_REPO),
            capture_output=True,
            text=True,
            timeout=120,
        )
        self.assertEqual(
            proc.returncode,
            0,
            msg=(proc.stdout or "") + (proc.stderr or ""),
        )
        self.assertIn("[OK] Repository health check passed.", proc.stdout)


if __name__ == "__main__":
    unittest.main()
