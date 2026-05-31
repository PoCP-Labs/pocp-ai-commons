#!/usr/bin/env python3
"""Run compute auto-balance cycle (surplus recycle) — for cron or operators."""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal, init_db
from services.compute_balance_cron import run_auto_balance_cycle


def main() -> int:
    parser = argparse.ArgumentParser(description="PoCP compute auto-balance cycle")
    parser.add_argument("--org", dest="organization_entity_id", default=None, help="Org entity id")
    parser.add_argument("--dry-run", action="store_true", help="Report actions without recycle")
    parser.add_argument("--force", action="store_true", help="Run even if auto_balance disabled")
    args = parser.parse_args()

    init_db()
    db = SessionLocal()
    try:
        result = run_auto_balance_cycle(
            db,
            organization_entity_id=args.organization_entity_id,
            dry_run=args.dry_run,
            force=args.force or args.dry_run,
        )
        if result.get("status") == "completed" and not args.dry_run:
            db.commit()
        else:
            db.rollback()
        print(json.dumps(result, indent=2, default=str))
        return 0 if result.get("status") in ("completed", "skipped", "disabled") else 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
