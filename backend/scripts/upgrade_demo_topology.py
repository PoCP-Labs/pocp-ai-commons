"""Upgrade existing demo DB to extended Entity ontology (tool, dataset, witness roles).

Safe to run on a live database — idempotent. Does not delete contributions or ledger rows.

Usage:
  python scripts/upgrade_demo_topology.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from database import SessionLocal  # noqa: E402
from seed import upgrade_demo_pilot_topology  # noqa: E402


def main() -> int:
    db = SessionLocal()
    try:
        changed = upgrade_demo_pilot_topology(db)
        if changed:
            db.commit()
            print("Demo pilot topology upgraded (participants and/or evidence updated).")
        else:
            print("Demo pilot topology already up to date (or demo contribution not found).")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
