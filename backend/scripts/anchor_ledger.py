"""Export daily ledger anchor (Merkle root of record hashes)."""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from database import SessionLocal, init_db
from services.ledger_anchor import build_ledger_anchor


def main() -> None:
    out_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("anchors")
    out_dir.mkdir(parents=True, exist_ok=True)
    init_db()
    db = SessionLocal()
    try:
        anchor = build_ledger_anchor(db)
    finally:
        db.close()

    node_id = anchor.get("node_id", "unknown")
    node_dir = out_dir / node_id
    node_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    out_path = node_dir / f"ledger-anchor-{stamp}.json"
    out_path.write_text(json.dumps(anchor, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(anchor, indent=2, ensure_ascii=False))
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
