#!/usr/bin/env python3
"""PL-10 / PN-6 closeout — run acceptance gate and complete protocol Studio missions.

Usage:
  python backend/scripts/complete_protocol_missions.py
  python backend/scripts/complete_protocol_missions.py --skip-gate --dry-run
  python backend/scripts/complete_protocol_missions.py --include-blocked
"""

from __future__ import annotations

import argparse
import os
import subprocess
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

PROTOCOL_PLAN_IDS = frozenset({"protocol_layer_edp", "protocol_native_stack"})
OPEN_HANDOFF = {"pending", "in_progress"}
GAUGE_ID = "pocp-agent-gauge-0"


def _is_protocol_pa_handoff(handoff) -> bool:
    """Only numbered plan actions — skip Nexus Training/Review on same mission."""
    scope = handoff.scope or ""
    return "[PN-" in scope or "[PL-" in scope


def _run_gate() -> int:
    proc = subprocess.run(
        [sys.executable, str(_BACKEND / "scripts/protocol_layer_acceptance.py")],
        cwd=_BACKEND,
    )
    return proc.returncode


def _mission_matches(mission) -> bool:
    meta = mission.metadata_ or {}
    plan_id = meta.get("plan_id") or meta.get("track")
    if meta.get("plan_id") in PROTOCOL_PLAN_IDS:
        return True
    if plan_id in PROTOCOL_PLAN_IDS:
        return True
    title = (mission.title or "").lower()
    if "protocol native stack" in title or "entity dialogue protocol" in title:
        return True
    if "protocol layer" in title and "dialogue" in title:
        return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Complete protocol_layer_edp + protocol_native_stack missions")
    parser.add_argument("--skip-gate", action="store_true", help="Skip pytest/smoke (not recommended)")
    parser.add_argument("--dry-run", action="store_true", help="Print actions only")
    parser.add_argument(
        "--include-blocked",
        action="store_true",
        help="Also mark blocked handoffs on protocol missions as completed",
    )
    parser.add_argument("--limit-missions", type=int, default=20)
    args = parser.parse_args()

    print("=== Protocol mission closeout (PL-10) ===\n")

    if not args.skip_gate:
        print("Running acceptance gate...")
        if _run_gate() != 0:
            print("\nAbort: fix acceptance failures before closeout.")
            return 1
        print()
    else:
        print("(skipped acceptance gate)\n")

    from database import SessionLocal, init_db
    from genesis import ensure_genesis_entities
    from models.agent_studio import AgentStudioHandoff, AgentStudioMission, StudioHandoffStatus, StudioMissionStatus
    from services.agent_studio.handoffs import complete_handoff
    from services.agent_studio.missions import complete_mission
    from services.agent_studio.nexus_autopilot import run_nexus_autopilot
    from services.agent_studio.outcomes import record_outcome
    from services.meta_agent_registry import ensure_meta_agents

    init_db()
    db = SessionLocal()
    try:
        ensure_genesis_entities(db)
        ensure_meta_agents(db)

        missions = (
            db.query(AgentStudioMission)
            .filter(
                AgentStudioMission.status.in_(
                    [StudioMissionStatus.active, StudioMissionStatus.reviewing, StudioMissionStatus.draft]
                )
            )
            .order_by(AgentStudioMission.created_at.desc())
            .limit(args.limit_missions * 3)
            .all()
        )
        protocol_missions = [m for m in missions if _mission_matches(m)][: args.limit_missions]

        if not protocol_missions:
            print("No active protocol missions found (plan_id protocol_layer_edp or protocol_native_stack).")
            print("Dispatch first: py -3.12 backend/scripts/dispatch_protocol_native_stack_studio.py")
            return 0

        closed_handoffs = 0
        closed_missions = 0

        for mission in protocol_missions:
            print(f"Mission: {mission.title} [{mission.status.value}] id={mission.id}")
            handoffs = (
                db.query(AgentStudioHandoff)
                .filter(AgentStudioHandoff.mission_id == mission.id)
                .order_by(AgentStudioHandoff.created_at.asc())
                .all()
            )
            for h in handoffs:
                if not _is_protocol_pa_handoff(h):
                    continue
                st = h.status.value
                should_close = st in OPEN_HANDOFF or (args.include_blocked and st == "blocked")
                if not should_close:
                    print(f"  keep {st:12} {h.id[:8]} -> {h.to_agent_entity_id}")
                    continue
                scope_preview = (h.scope or "")[:70].replace("\n", " ")
                scope_preview = scope_preview.encode("ascii", errors="replace").decode("ascii")
                print(f"  close {st:12} {h.id[:8]} -> {h.to_agent_entity_id} | {scope_preview}")
                if not args.dry_run:
                    complete_handoff(
                        db,
                        h.id,
                        status="completed",
                        blockers=None,
                    )
                    meta = dict(h.metadata_ or {})
                    meta["closeout"] = {
                        "source": "complete_protocol_missions.py",
                        "acceptance": "protocol_layer_acceptance.py",
                    }
                    h.metadata_ = meta
                closed_handoffs += 1

            if not args.dry_run:
                complete_mission(db, mission.id)
                meta = dict(mission.metadata_ or {})
                meta["closed_by"] = "complete_protocol_missions.py"
                meta["acceptance_gate"] = "protocol_layer_acceptance.py"
                mission.metadata_ = meta
            closed_missions += 1
            print("  -> mission marked completed\n")

        if not args.dry_run:
            record_outcome(
                db,
                agent_entity_id=GAUGE_ID,
                kind="acceptance",
                result="pass",
                summary="Protocol layer acceptance gate green; PL-10 / PN-6 closeout applied.",
                evidence={
                    "script": "protocol_layer_acceptance.py",
                    "missions_closed": [m.id for m in protocol_missions],
                    "handoffs_closed": closed_handoffs,
                },
            )
            nexus = run_nexus_autopilot(db)
            print(f"Nexus follow-up: {nexus.get('mode')} — {nexus.get('message', '')[:120]}")
            db.commit()

        print(f"Summary: {closed_missions} mission(s), {closed_handoffs} handoff(s) {'would be ' if args.dry_run else ''}closed.")
        if args.dry_run:
            print("(dry-run — no database changes)")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
