#!/usr/bin/env python3
"""CLI: register all PoCP Meta Agents as protocol Entities."""

import os
import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[1]
os.chdir(_BACKEND)
sys.path.insert(0, str(_BACKEND))

from database import SessionLocal, init_db
from services.meta_agent_registry import ensure_meta_agents, list_meta_agents


def main() -> int:
    init_db()
    db = SessionLocal()
    try:
        ids = ensure_meta_agents(db)
        db.commit()
        print(f"Ensured {len(ids)} Meta Agents:")
        for row in list_meta_agents(db):
            cap = row.get("cursor_capabilities") or {}
            ok = "ok" if cap.get("prompt_available") else "missing prompt"
            print(f"  - {row['entity_id']} ({row['task_label']}) prompt={ok}")
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
