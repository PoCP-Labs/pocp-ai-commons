#!/usr/bin/env python3
"""List Agent Studio handoff queue (pending / blocked / in_progress)."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[1]
os.chdir(_BACKEND)
sys.path.insert(0, str(_BACKEND))

try:
    from dotenv import load_dotenv

    load_dotenv(_BACKEND / ".env", override=False)
except ImportError:
    pass

from database import SessionLocal, init_db
from models.agent_studio import AgentStudioHandoff, StudioHandoffStatus
from meta_agents_spec import META_AGENT_BY_ID


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--status", choices=["pending", "blocked", "in_progress", "completed", "all"], default="all")
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument("--retry-blocked", action="store_true", help="Reset blocked handoffs to pending")
    args = parser.parse_args()

    init_db()
    db = SessionLocal()
    try:
        if args.retry_blocked:
            rows = (
                db.query(AgentStudioHandoff)
                .filter(AgentStudioHandoff.status == StudioHandoffStatus.blocked)
                .all()
            )
            for h in rows:
                h.status = StudioHandoffStatus.pending
                meta = dict(h.metadata_ or {})
                meta.pop("blockers", None)
                h.metadata_ = meta
            db.commit()
            print(f"Reset {len(rows)} blocked handoff(s) to pending.")
            return 0

        q = db.query(AgentStudioHandoff).order_by(AgentStudioHandoff.created_at.desc())
        if args.status != "all":
            q = q.filter(AgentStudioHandoff.status == StudioHandoffStatus(args.status))
        rows = q.limit(args.limit).all()

        print(f"=== Handoffs ({args.status}, limit={args.limit}) ===\n")
        for h in rows:
            spec = META_AGENT_BY_ID.get(h.to_agent_entity_id, {})
            name = spec.get("name", h.to_agent_entity_id)
            blockers = (h.metadata_ or {}).get("blockers") or ""
            cursor = (h.metadata_ or {}).get("cursor_execution") or {}
            summary = (cursor.get("summary") or cursor.get("message") or "")[:120]
            print(f"{h.status.value:12} {h.id[:8]}… → {name}")
            print(f"             {(h.scope or '')[:100]}")
            if blockers:
                print(f"             blockers: {blockers[:120]}")
            elif summary:
                print(f"             cursor: {summary}")
            print()
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
