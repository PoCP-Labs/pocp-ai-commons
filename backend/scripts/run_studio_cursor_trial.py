#!/usr/bin/env python3
"""One visible Agent Studio + Cursor trial — streams progress to the terminal."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_WORKER = _REPO / "backend" / "scripts" / "run_studio_cursor_worker.py"


def main() -> int:
    env = os.environ.copy()
    env["POCP_STUDIO_VERBOSE"] = "true"
    env["POCP_CURSOR_WORKER_ONCE"] = "true"
    env.setdefault("POCP_CURSOR_AUTOMATION", "true")
    env.setdefault("POCP_REPO_ROOT", str(_REPO))

    print("Starting verbose trial (Nexus → 1 handoff → Cursor live output)\n", flush=True)
    print("Press Ctrl+C to cancel.\n", flush=True)

    result = subprocess.run(
        [sys.executable, str(_WORKER), "--verbose", "--once"],
        cwd=str(_REPO),
        env=env,
    )
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
