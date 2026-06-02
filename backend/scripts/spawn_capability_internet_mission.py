#!/usr/bin/env python3
"""Spawn Capability Internet mission + handoffs for Agent Studio."""

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
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.dry_run:
        plans = list_mission_plans()
        ci = next((p for p in plans if p["id"] == "capability_internet"), None)
        print(json.dumps(ci or {}, indent=2) if args.json else ci)
        return 0

    db = SessionLocal()
    try:
        ensure_genesis_entities(db)
        ensure_meta_agents(db)
        result = create_mission_from_plan(db, "capability_internet", activate=True, spawn_handoffs=True)
        db.commit()
        if args.json:
            print(json.dumps(result, indent=2, default=str))
        else:
            m = result["mission"]
            print(f"Mission: {m['title']}")
            print(f"Handoffs: {result['handoff_count']}")
            for h in result["handoffs"]:
                print(f"  → {h['to_agent_entity_id']}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
