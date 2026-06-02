#!/usr/bin/env python3
"""Dispatch Protocol Native Stack mission (PN-1..PN-6) to Agent Studio.

Usage:
  py -3.12 backend/scripts/dispatch_protocol_native_stack_studio.py
  py -3.12 backend/scripts/dispatch_protocol_native_stack_studio.py --cursor-tick
  py -3.12 backend/scripts/dispatch_protocol_native_stack_studio.py --api http://127.0.0.1:8008
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_BACKEND = _REPO / "backend"
sys.path.insert(0, str(_BACKEND))

try:
    from dotenv import load_dotenv

    load_dotenv(_BACKEND / ".env", override=False)
except ImportError:
    pass

PLAN_ID = "protocol_native_stack"


def _api(base: str, method: str, path: str, body: dict | None = None) -> dict:
    url = f"{base.rstrip('/')}{path}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method=method,
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _dispatch_in_process() -> dict:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from database import Base
    from genesis import ensure_genesis_entities
    from models.agent_studio import AgentStudioMission
    from services.agent_studio.mission_plans import create_mission_from_plan
    from services.agent_studio.nexus_autopilot import run_nexus_autopilot
    from services.meta_agent_registry import ensure_meta_agents

    db_url = os.getenv("DATABASE_URL", f"sqlite:///{_BACKEND / 'pocp.db'}")
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        ensure_genesis_entities(db)
        ensure_meta_agents(db)
        result = create_mission_from_plan(db, PLAN_ID, activate=True, spawn_handoffs=True)
        mission = result["mission"]
        if mission.get("id"):
            row = db.get(AgentStudioMission, mission["id"])
            if row is not None:
                row.metadata_ = {
                    **(row.metadata_ or {}),
                    "plan_id": PLAN_ID,
                    "track": "protocol_native_stack",
                    "handoffs": [f"PN-{i}" for i in range(1, 7)],
                }
                db.flush()
        nexus = run_nexus_autopilot(db)
        db.commit()
        return {"mode": "in_process", "mission": result, "nexus": nexus}
    finally:
        db.close()


def _dispatch_via_api(base: str) -> dict:
    _api(base, "POST", "/api/v1/agent-studio/ensure-agents")
    mission = _api(base, "POST", f"/api/v1/agent-studio/missions/from-plan/{PLAN_ID}")
    nexus = _api(base, "POST", "/api/v1/agent-studio/nexus/autopilot")
    return {"mode": "api", "base": base, "mission": mission, "nexus": nexus}


def _cursor_tick(base: str | None) -> dict:
    if base:
        try:
            return _api(base, "POST", "/api/v1/agent-studio/cursor/run?max_handoffs=1")
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            return {"ran": False, "error": body[:500]}

    if sys.version_info < (3, 12):
        return {
            "ran": False,
            "reason": "Cursor tick in-process requires Python 3.12+",
        }

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from database import Base
    from services.agent_studio.cursor_automation import run_cursor_automation_tick
    from services.meta_agent_registry import ensure_meta_agents

    db_url = os.getenv("DATABASE_URL", f"sqlite:///{_BACKEND / 'pocp.db'}")
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        ensure_meta_agents(db)
        result = run_cursor_automation_tick(db, max_handoffs=1)
        db.commit()
        return result
    finally:
        db.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Dispatch protocol_native_stack mission")
    parser.add_argument("--api", default=os.getenv("POCP_API_BASE", ""), help="API base (empty = in-process)")
    parser.add_argument("--cursor-tick", action="store_true", help="Run one Cursor handoff after dispatch")
    parser.add_argument("--gate", action="store_true", help="Run PN-6 acceptance tests + network smoke")
    args = parser.parse_args()

    print(f"\n=== Protocol Native Stack Studio Dispatch ===\nplan_id={PLAN_ID}\n")

    if args.gate:
        import shutil
        import subprocess

        pytest_cmd = shutil.which("python") or sys.executable
        print(f"PN-6 gate: pytest ({pytest_cmd}) + network smoke...")
        tests = subprocess.run(
            [
                pytest_cmd,
                "-m",
                "pytest",
                "tests/test_entity_dialogue.py",
                "tests/test_protocol_network.py",
                "tests/test_federation_overlay.py",
                "tests/test_merkle_canonical.py",
                "-q",
            ],
            cwd=_BACKEND,
        )
        smoke = subprocess.run(
            [sys.executable, str(_REPO / "backend/scripts/bitcoin_inspired_network_smoke.py")],
            cwd=_REPO,
        )
        if tests.returncode != 0 or smoke.returncode != 0:
            print("Gate FAILED — fix tests before marking PN-6 complete.")
            return 1
        print("Gate PASSED.\n")

    try:
        if args.api.strip():
            payload = _dispatch_via_api(args.api.strip())
        else:
            payload = _dispatch_in_process()
    except Exception as exc:
        print(f"Dispatch FAILED: {exc}")
        return 1

    mission = payload.get("mission") or {}
    handoff_count = mission.get("handoff_count") or len(mission.get("handoffs") or [])
    mid = (mission.get("mission") or {}).get("id") or mission.get("id")
    print(f"Mission: {mid}")
    print(f"Handoffs spawned (PA): {handoff_count}")
    print(f"Mode: {payload.get('mode')}")

    if args.cursor_tick:
        print("\nRunning Cursor automation tick (1 handoff)...")
        tick = _cursor_tick(args.api.strip() or None)
        processed = tick.get("processed") or []
        if processed:
            print(f"  processed: {len(processed)} handoff(s)")
            for p in processed:
                print(f"    - {p.get('handoff_id')}: {p.get('status')}")
        else:
            print(f"  skipped: {tick.get('reason') or tick.get('error') or tick.get('errors') or 'no work'}")

    print("\nNext:")
    print("  py -3.12 backend/scripts/run_studio_cursor_worker.py --once --verbose")
    print("  agents/missions/protocol-native-stack/MANIFEST.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
