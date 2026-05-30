"""Sync code attribution registry to DB, ledger, and reputation.

Usage:
  python scripts/sync_code_attribution.py --report
  python scripts/sync_code_attribution.py --sync
  python scripts/sync_code_attribution.py --sync --award-reputation
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from database import SessionLocal, init_db
from services.code_attribution import (
    append_code_attribution_ledger,
    award_registry_reputation,
    ensure_builder_entities,
    scan_repository,
    sync_scan_to_records,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="PoCP code attribution sync")
    parser.add_argument("--report", action="store_true", help="Print scan report only")
    parser.add_argument("--sync", action="store_true", help="Persist records + entities")
    parser.add_argument("--award-reputation", action="store_true", help="Update code_registry reputation")
    parser.add_argument("--ledger", action="store_true", default=True, help="Append ledger event")
    parser.add_argument("--no-ledger", action="store_true", help="Skip ledger write")
    args = parser.parse_args()

    if args.report and not args.sync:
        report = scan_repository()
        for slug, info in sorted(report["builders"].items(), key=lambda x: -x[1]["lines"]):
            print(
                f"{info['display_name']:16}  files={info['file_count']:4}  lines={info['lines']:6}  "
                f"status={info.get('status', '?')}"
            )
        print(f"\nUnassigned files: {report['unassigned_file_count']}  lines: {report['unassigned_lines']}")
        return

    if not args.sync:
        parser.print_help()
        return

    init_db()
    db = SessionLocal()
    try:
        ensure_builder_entities(db)
        counts = sync_scan_to_records(db)
        report = scan_repository()
        print(f"Records inserted={counts['inserted']} skipped={counts['skipped']}")
        if args.award_reputation:
            awarded = award_registry_reputation(db)
            print("Reputation awarded:", json.dumps(awarded, indent=2))
        if args.ledger and not args.no_ledger:
            summary = {
                "records": counts,
                "builder_file_counts": {s: b["file_count"] for s, b in report["builders"].items()},
            }
            rec = append_code_attribution_ledger(db, summary)
            print(f"Ledger record: {rec.id}")
        db.commit()
        print("OK code attribution sync complete")
    finally:
        db.close()


if __name__ == "__main__":
    main()
