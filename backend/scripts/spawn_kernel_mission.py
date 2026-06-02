#!/usr/bin/env python3
"""Spawn Phase A Kernel mission + handoffs for Agent Studio / Nexus-0."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=False)
except ImportError:
    pass

from database import SessionLocal
from genesis import ensure_genesis_entities
from services.agent_studio.mission_plans import create_mission_from_plan, list_mission_plans
from services.meta_agent_registry import ensure_meta_agents


def main() -> int:
    parser = argparse.ArgumentParser(description="Spawn phase_a_kernel Agent Studio mission")
    parser.add_argument("--json", action="store_true", help="JSON output only")
    parser.add_argument("--dry-run", action="store_true", help="List plan handoffs without creating")
    args = parser.parse_args()

    if args.dry_run:
        plans = list_mission_plans()
        kernel = next((p for p in plans if p["id"] == "phase_a_kernel"), None)
        if args.json:
            print(json.dumps(kernel or {}, indent=2))
        else:
            print("phase_a_kernel plan:", kernel)
        return 0

    db = SessionLocal()
    try:
        ensure_genesis_entities(db)
        ensure_meta_agents(db)
        result = create_mission_from_plan(db, "phase_a_kernel", activate=True, spawn_handoffs=True)
        db.commit()
        if args.json:
            print(json.dumps(result, indent=2, default=str))
        else:
            mission = result["mission"]
            print(f"Mission: {mission['title']} ({mission['id']})")
            print(f"Handoffs spawned: {result['handoff_count']}")
            for h in result["handoffs"]:
                print(f"  → {h['to_agent_entity_id']}: {h['scope'][:80]}…")
            print("\nOpen Agent Studio tab or GET /api/v1/agent-studio/handoffs")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
