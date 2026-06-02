#!/usr/bin/env python3
"""Cross-check Agent Studio handoffs vs docs/ROADMAP-THREE-PHASES local optimization priorities.

Compass-0 / Nexus-0: run from repo root:
  python agents/scripts/roadmap_handoff_crosscheck.py
  python agents/scripts/roadmap_handoff_crosscheck.py --mission fa62e623-a98e-464e-b6e7-3f4ab95e992d
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from database import SessionLocal  # noqa: E402
from models.agent_studio import AgentStudioHandoff, StudioHandoffStatus  # noqa: E402
from services.agent_studio.nexus_autopilot import PROJECT_GOALS  # noqa: E402

P0_AGENTS = {
    "pocp-agent-vault-0",
    "pocp-agent-mesh-0",
    "pocp-agent-gauge-0",
}

META_SCOPES = ("[Nexus Training]", "[Nexus Research]", "[Nexus Review]")


def _classify(scope: str | None) -> str:
    s = scope or ""
    for prefix in META_SCOPES:
        if s.startswith(prefix):
            return prefix.strip("[]").replace(" ", "_").lower()
    if any(k in s.lower() for k in ("exchange", "wallet", "federation", "compute")):
        return "engineering"
    return "other"


def run(*, mission_id: str | None = None) -> int:
    db = SessionLocal()
    try:
        q = db.query(AgentStudioHandoff)
        if mission_id:
            q = q.filter(AgentStudioHandoff.mission_id == mission_id)
        handoffs = q.all()

        open_status = {StudioHandoffStatus.pending, StudioHandoffStatus.in_progress}
        open_h = [h for h in handoffs if h.status in open_status]
        blocked_p0 = [
            h
            for h in handoffs
            if h.status == StudioHandoffStatus.blocked
            and h.to_agent_entity_id in P0_AGENTS
            and _classify(h.scope) == "engineering"
        ]

        pending_by_class = Counter(_classify(h.scope) for h in open_h)
        pending_p0_eng = [
            h for h in open_h if h.to_agent_entity_id in P0_AGENTS and _classify(h.scope) == "engineering"
        ]

        print("=== Roadmap handoff cross-check ===")
        if mission_id:
            print(f"mission_id: {mission_id}")
        print(f"handoffs_total: {len(handoffs)}")
        print(f"open (pending+in_progress): {len(open_h)}")
        print(f"  by class: {dict(pending_by_class)}")
        print(f"open P0 engineering (vault/mesh/gauge): {len(pending_p0_eng)}")
        print(f"blocked P0 engineering: {len(blocked_p0)}")
        print()
        print("PROJECT_GOALS (Nexus autopilot):")
        for g in sorted(PROJECT_GOALS, key=lambda x: (x["priority"], x["id"])):
            print(f"  {g['phase']} {g['id']} -> {g['owner_agent_id']}")
        print()
        if open_h:
            print("Open handoffs (newest first):")
            for h in sorted(open_h, key=lambda x: x.created_at or "", reverse=True):
                print(
                    f"  {h.id[:8]}… {h.status.value:10} "
                    f"{h.to_agent_entity_id.split('-')[-2]:8} "
                    f"[{_classify(h.scope)}] {(h.scope or '')[:60]}"
                )
        else:
            print("No open handoffs.")

        # Pass when P0 engineering is not starved by meta-only queue
        meta_open = sum(1 for h in open_h if _classify(h.scope) in ("nexus_training", "nexus_research", "nexus_review"))
        fail = bool(blocked_p0) and not pending_p0_eng and meta_open >= 3
        if fail:
            print()
            print(
                "FAIL: P0 engineering handoffs blocked; open queue is meta/coaching "
                f"({meta_open} items). Re-prioritize Cursor dispatch to Vault/Mesh/Gauge."
            )
            return 1
        print()
        print("PASS: queue state acceptable for roadmap alignment check.")
        return 0
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mission", default=None, help="Filter to mission UUID")
    args = parser.parse_args()
    raise SystemExit(run(mission_id=args.mission))


if __name__ == "__main__":
    main()
