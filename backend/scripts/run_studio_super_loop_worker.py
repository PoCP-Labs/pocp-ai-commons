#!/usr/bin/env python3
"""
Nexus super-loop on the HOST (recommended on Windows with Docker backend).

One tick: health probe → Nexus plan/dispatch → Cursor handoffs → PDCA → platform repair.

  py -3.12 backend/scripts/run_studio_super_loop_worker.py --verbose --once
  POCP_SUPER_LOOP_WORKER_ONCE=true py -3.12 backend/scripts/run_studio_super_loop_worker.py
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
    os.environ.setdefault("BACKEND_URL", "http://127.0.0.1:8008")
    os.environ.setdefault("POCP_CURSOR_AUTOMATION", "true")
    os.environ.setdefault("POCP_NEXUS_AUTOPILOT", "true")
    os.environ.setdefault("POCP_NEXUS_SUPER_LOOP_HOST", "true")
    os.environ.setdefault("POCP_NEXUS_SUPER_LOOP", "false")
    os.environ.setdefault("POCP_STUDIO_AUTO_EVOLVE", "true")


_load_env()

from database import SessionLocal, init_db  # noqa: E402
from services.agent_studio.cursor_automation import automation_status  # noqa: E402
from services.agent_studio.nexus_super_loop import run_nexus_super_tick  # noqa: E402
from services.agent_studio.studio_console import (  # noqa: E402
    configure_studio_stdio,
    log_banner,
    log_step,
)

configure_studio_stdio()
from services.meta_agent_registry import ensure_meta_agents  # noqa: E402


def _require_python_312() -> None:
    if sys.version_info >= (3, 12):
        return
    print(
        "ERROR: Super-loop requires Python 3.12+ for Cursor SDK.\n"
        f"  Current: {sys.version.split()[0]}\n"
        "  Run: py -3.12 backend/scripts/run_studio_super_loop_worker.py --verbose --once",
        flush=True,
    )
    raise SystemExit(1)


def _print_tick(tick: dict, *, verbose: bool) -> None:
    nexus = tick.get("nexus") or {}
    cursor = tick.get("cursor") or {}
    log_step(
        "Nexus",
        f"mode={nexus.get('mode')} pending={tick.get('pending_for_cursor')} "
        f"healthy={tick.get('platform_healthy')}",
    )
    log_step("Cursor", f"processed={cursor.get('processed_count', 0)}")
    if tick.get("human_required"):
        for r in tick.get("human_required_reasons") or []:
            log_step("Human review", r)
    if verbose:
        for step in tick.get("steps") or []:
            phase = step.get("phase", "?")
            if step.get("error"):
                log_step(phase, f"error={step['error']}")
            elif step.get("skipped"):
                log_step(phase, str(step.get("skipped") or step.get("reason", "skipped")))
        for item in cursor.get("processed") or []:
            c = item.get("cursor") or {}
            log_step(
                "Handoff",
                f"{item.get('handoff_id')} status={item.get('status')} ok={c.get('ok')}",
            )
            if verbose and c.get("summary"):
                print((c.get("summary") or "")[:1200], flush=True)


def main() -> int:
    _require_python_312()
    parser = argparse.ArgumentParser(description="Nexus super-loop host worker")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("--once", action="store_true", help="One tick then exit")
    parser.add_argument(
        "--max-cursor",
        type=int,
        default=None,
        help="Override POCP_SUPER_LOOP_MAX_CURSOR_PER_TICK",
    )
    args = parser.parse_args()

    verbose = args.verbose or os.getenv("POCP_STUDIO_VERBOSE", "false").lower() in (
        "1",
        "true",
        "yes",
    )
    once = args.once or os.getenv("POCP_SUPER_LOOP_WORKER_ONCE", "false").lower() in (
        "1",
        "true",
        "yes",
    )
    max_cursor = args.max_cursor
    if max_cursor is None:
        try:
            max_cursor = int(os.getenv("POCP_SUPER_LOOP_MAX_CURSOR_PER_TICK", "2"))
        except ValueError:
            max_cursor = 2

    if verbose:
        log_banner("Agent Studio — Nexus super-loop (host worker)")

    init_db()
    status = automation_status()
    if not status.get("api_key_configured"):
        print("Set CURSOR_API_KEY in backend/.env")
        return 1
    if verbose:
        log_step(
            "Environment",
            f"repo={status.get('repo_root')} backend={os.getenv('BACKEND_URL')} "
            f"sdk={status.get('sdk_installed')}",
        )

    interval = int(os.getenv("POCP_NEXUS_SUPER_LOOP_INTERVAL_SEC", "600"))
    tick_num = 0
    while True:
        tick_num += 1
        if verbose:
            log_step(f"Super tick #{tick_num}", "starting")

        db = SessionLocal()
        try:
            ensure_meta_agents(db)
            tick = run_nexus_super_tick(db, max_cursor_handoffs=max_cursor)
            db.commit()
            if verbose:
                _print_tick(tick, verbose=verbose)
            else:
                nexus = tick.get("nexus") or {}
                cursor = tick.get("cursor") or {}
                print(
                    f"[{tick.get('at')}] nexus={nexus.get('mode')} "
                    f"cursor={cursor.get('processed_count')} "
                    f"pending={tick.get('pending_for_cursor')} "
                    f"human_required={tick.get('human_required')}",
                    flush=True,
                )
        except Exception as exc:
            db.rollback()
            print("super tick failed:", exc, flush=True)
            if verbose:
                import traceback

                traceback.print_exc()
            return 1
        finally:
            db.close()

        if once:
            if verbose:
                log_banner("Super-loop trial finished")
            break
        if verbose:
            log_step("Sleeping", f"{interval}s (Ctrl+C to stop)")
        time.sleep(interval)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
