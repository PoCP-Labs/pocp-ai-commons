#!/usr/bin/env python3
"""Pre-flight for Nexus super-loop host worker."""

from __future__ import annotations

import os
import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[1]
_REPO = _BACKEND.parent
sys.path.insert(0, str(_BACKEND))
os.chdir(_BACKEND)

try:
    from dotenv import load_dotenv

    load_dotenv(_BACKEND / ".env", override=False)
except ImportError:
    pass

os.environ.setdefault("POCP_REPO_ROOT", str(_REPO))
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://pocp:pocp@127.0.0.1:5435/pocp")
os.environ.setdefault("BACKEND_URL", "http://127.0.0.1:8008")

from database import SessionLocal, init_db  # noqa: E402
from services.agent_studio.cursor_automation import automation_status  # noqa: E402
from services.agent_studio.nexus_super_loop import super_loop_status  # noqa: E402
from services.agent_studio.platform_health import probe_platform  # noqa: E402


def _ok(msg: str) -> None:
    print(f"  OK   {msg}")


def _fail(msg: str) -> None:
    print(f"  FAIL {msg}")


def main() -> int:
    errors = 0
    print("=== Nexus super-loop pre-flight ===\n")

    if sys.version_info < (3, 12):
        _fail(f"Python 3.12+ required (current {sys.version.split()[0]})")
        errors += 1
    else:
        _ok(f"Python {sys.version.split()[0]}")

    status = super_loop_status()
    if status.get("host_mode"):
        _ok("POCP_NEXUS_SUPER_LOOP_HOST=true (host owns loop)")
    else:
        _fail("Set POCP_NEXUS_SUPER_LOOP_HOST=true in backend/.env for Windows host worker")
        errors += 1

    if not status.get("backend_loop_active"):
        _ok("Docker backend super-loop disabled (no double-run)")
    else:
        _fail("POCP_NEXUS_SUPER_LOOP=true in backend — disable when using host worker")
        errors += 1

    cursor = automation_status()
    if cursor.get("sdk_installed"):
        _ok("cursor-sdk installed")
    else:
        _fail("pip install cursor-sdk (py -3.12 -m pip install cursor-sdk)")
        errors += 1
    if cursor.get("api_key_configured"):
        _ok("CURSOR_API_KEY set")
    else:
        _fail("CURSOR_API_KEY missing in backend/.env")
        errors += 1

    init_db()
    db = SessionLocal()
    try:
        health = None
        for attempt in range(1, 4):
            health = probe_platform(db)
            if health.get("ok"):
                break
            if attempt < 3:
                import time

                time.sleep(5)
        if health and health.get("ok"):
            _ok(f"platform healthy ({health.get('api', {}).get('base')})")
        else:
            for issue in (health or {}).get("issues") or []:
                _fail(issue)
            errors += 1
    finally:
        db.close()

    print()
    if errors:
        print(f"Fix {errors} item(s), then: .\\scripts\\run-studio-super-loop.ps1")
        return 1
    print("Ready. Start worker: .\\scripts\\run-studio-super-loop.ps1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
