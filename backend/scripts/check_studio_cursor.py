#!/usr/bin/env python3
"""Check Agent Studio → Cursor automation readiness (no API calls)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[1]
_REPO = _BACKEND.parent
os.chdir(_BACKEND)
sys.path.insert(0, str(_BACKEND))

try:
    from dotenv import load_dotenv

    load_dotenv(_BACKEND / ".env", override=False)
except ImportError:
    pass

os.environ.setdefault("POCP_REPO_ROOT", str(_REPO))
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://pocp:pocp@127.0.0.1:5435/pocp")

from services.agent_studio.cursor_automation import count_pending_for_cursor  # noqa: E402
from services.agent_studio.cursor_bridge import (  # noqa: E402
    automation_enabled,
    automation_status,
    bridge_launch_ok,
    python_supports_cursor_sdk,
)
from database import SessionLocal, init_db  # noqa: E402


def main() -> int:
    init_db()
    status = automation_status()
    key_set = bool(status.get("api_key_configured"))
    print("=== Agent Studio Cursor readiness ===")
    print(f"  python               : {sys.version.split()[0]} ({sys.executable})")
    print(f"  python >= 3.12       : {python_supports_cursor_sdk()}")
    print(f"  cursor-sdk installed : {status.get('sdk_installed')}")
    print(f"  CURSOR_API_KEY set   : {key_set}")
    print(f"  POCP_CURSOR_AUTOMATION: {status.get('enabled_flag')}")
    print(f"  automation_active    : {status.get('automation_active')}")
    print(f"  repo_root            : {status.get('repo_root')}")
    print(f"  model                : {status.get('model')}")
    db = SessionLocal()
    try:
        pending = count_pending_for_cursor(db)
    finally:
        db.close()
    print(f"  pending handoffs     : {pending}")
    bridge_ok = True
    if python_supports_cursor_sdk() and status.get("sdk_installed"):
        bridge_ok, msg = bridge_launch_ok()
        print(f"  bridge launch        : {bridge_ok} ({msg})")
    if not key_set:
        print("\nAdd to backend/.env:")
        print("  CURSOR_API_KEY=cursor_...")
        print("  POCP_CURSOR_AUTOMATION=true")
    if not python_supports_cursor_sdk():
        print("\nUse Python 3.12+: py -3.12 backend/scripts/check_studio_cursor.py")
    elif not status.get("sdk_installed"):
        print("\nRun: py -3.12 -m pip install cursor-sdk")
    if automation_enabled() and bridge_ok:
        print("\nReady. Run: .\\scripts\\run-studio-cursor-trial.ps1")
        if key_set:
            print(
                "If runs fail with AuthenticationError, regenerate the key at "
                "https://cursor.com/dashboard/integrations"
            )
        return 0
    if automation_enabled() and not bridge_ok:
        print("\nBridge failed - see message above.")
        return 1
    print("\nNot ready yet — fix items above.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
