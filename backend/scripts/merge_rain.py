"""One-off: merge duplicate Rain entities into pocp-entity-rain."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from database import SessionLocal
from genesis import ensure_genesis_entities
from services.entity_dedup import merge_rain_duplicates


def main() -> None:
    db = SessionLocal()
    try:
        ensure_genesis_entities(db)
        merged = merge_rain_duplicates(db)
        db.commit()
        print(f"Merged {merged} duplicate Rain entit{'y' if merged == 1 else 'ies'}.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
