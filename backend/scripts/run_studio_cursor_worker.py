#!/usr/bin/env python3
"""
Run Agent Studio → Cursor automation on the HOST (recommended on Windows).

Verbose trial (see live Cursor output):
  python backend/scripts/run_studio_cursor_trial.py

Or:
  set POCP_STUDIO_VERBOSE=true
  set POCP_CURSOR_WORKER_ONCE=true
  python backend/scripts/run_studio_cursor_worker.py --verbose
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[1]
_REPO = _BACKEND.parent
os.chdir(_BACKEND)
sys.path.insert(0, str(_BACKEND))


def _load_env() -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv(_BACKEND / ".env", override=False)
    except ImportError:
        pass
    os.environ.setdefault("POCP_REPO_ROOT", str(_REPO))
    os.environ.setdefault(
        "DATABASE_URL", "postgresql+psycopg://pocp:pocp@127.0.0.1:5435/pocp"
    )
    os.environ.setdefault("POCP_CURSOR_AUTOMATION", "true")


_load_env()

from database import SessionLocal, init_db  # noqa: E402
from services.agent_studio.cursor_automation import (  # noqa: E402
    automation_enabled,
    automation_status,
    count_pending_for_cursor,
    run_cursor_automation_tick,
)
from services.agent_studio.nexus_autopilot import run_nexus_autopilot  # noqa: E402
from services.agent_studio.studio_console import (  # noqa: E402
    configure_studio_stdio,
    log_banner,
    log_step,
)

configure_studio_stdio()
from services.meta_agent_registry import ensure_meta_agents  # noqa: E402


def _print_nexus_summary(tick: dict) -> None:
    log_step("Nexus autopilot", f"mode={tick.get('mode')} - {tick.get('message', '')}")
    pr = tick.get("progress_review") or {}
    if pr:
        log_step(
            "Progress",
            f"completion={pr.get('completion_percent')}% "
            f"pending_handoffs={tick.get('pending_handoff_count')}",
        )
    dq = tick.get("dispatch_queue") or []
    if dq:
        log_step("Dispatch queue (top 3)")
        for item in dq[:3]:
            name = item.get("assignee_name", "?")
            scope = (item.get("scope") or "")[:80]
            print(f"         - {name}: {scope}", flush=True)


def _require_python_312() -> None:
    if sys.version_info >= (3, 12):
        return
    print(
        "ERROR: Cursor automation requires Python 3.12+ (cursor-sdk needs os.get_blocking).\n"
        f"  Current: {sys.version.split()[0]} ({sys.executable})\n"
        "  Run: py -3.12 backend/scripts/run_studio_cursor_worker.py --verbose --once",
        flush=True,
    )
    raise SystemExit(1)


def main() -> int:
    _require_python_312()
    parser = argparse.ArgumentParser(description="Agent Studio Cursor worker")
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Print Nexus steps, handoff details, and stream Cursor output",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Process one tick then exit (same as POCP_CURSOR_WORKER_ONCE=true)",
    )
    args = parser.parse_args()

    verbose = args.verbose or os.getenv("POCP_STUDIO_VERBOSE", "false").lower() in (
        "1",
        "true",
        "yes",
    )
    once = args.once or os.getenv("POCP_CURSOR_WORKER_ONCE", "false").lower() == "true"

    if verbose:
        log_banner("Agent Studio - Cursor automation (verbose trial)")

    init_db()
    status = automation_status()
    if verbose:
        log_step(
            "Environment",
            f"sdk={status.get('sdk_installed')} key={status.get('api_key_configured')} "
            f"repo={status.get('repo_root')}",
        )
    else:
        print("Cursor automation status:", status)

    if not automation_enabled():
        print("Not active. Set POCP_CURSOR_AUTOMATION=true, pip install cursor-sdk, CURSOR_API_KEY.")
        return 1

    interval = int(os.getenv("POCP_CURSOR_AUTOMATION_INTERVAL_SEC", "300"))

    db = SessionLocal()
    try:
        if verbose:
            log_step("Step 1/3", "Register Meta Agents + Nexus autopilot")
        ensure_meta_agents(db)
        nexus_tick = run_nexus_autopilot(db)
        db.commit()
        if verbose:
            _print_nexus_summary(nexus_tick)
            pending = count_pending_for_cursor(db)
            log_step("Step 2/3", f"{pending} handoff(s) ready for Cursor")
    finally:
        db.close()

    tick_num = 0
    while True:
        tick_num += 1
        if verbose:
            log_step(f"Step 3/3 - Cursor tick #{tick_num}", "Starting...")

        db = SessionLocal()
        try:
            tick = run_cursor_automation_tick(db, max_handoffs=1, verbose=verbose)
            db.commit()
            if verbose:
                for item in tick.get("processed") or []:
                    log_step(
                        "Handoff result",
                        f"id={item.get('handoff_id')} status={item.get('status')}",
                    )
                if tick.get("errors"):
                    log_step("Errors", "; ".join(tick["errors"]))
                nf = tick.get("nexus_followup_mode")
                if nf:
                    log_step("Nexus follow-up", f"mode={nf}")
            else:
                print(
                    f"[{tick.get('at')}] processed={len(tick.get('processed', []))} "
                    f"errors={tick.get('errors')}"
                )
        except Exception as exc:
            db.rollback()
            print("tick failed:", exc, flush=True)
            if verbose:
                import traceback

                traceback.print_exc()
            return 1
        finally:
            db.close()

        if once:
            if verbose:
                log_banner("Trial run finished - check Agent Studio for handoff status")
            break
        if verbose:
            log_step("Sleeping", f"{interval}s until next tick (Ctrl+C to stop)")
        time.sleep(interval)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
