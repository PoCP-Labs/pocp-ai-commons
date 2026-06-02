#!/usr/bin/env python3
"""Audit platform entity catalog and optionally run idempotent bootstrap."""

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
from seed import seed_demo
from services.entity_catalog import audit_entity_catalog, ensure_platform_entity_catalog
from services.org_foundation import ensure_pocp_org_foundation


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit and repair platform entity catalog")
    parser.add_argument(
        "--repair",
        action="store_true",
        help="Run idempotent bootstrap (infrastructure entities, capabilities, ownership)",
    )
    parser.add_argument(
        "--full-seed",
        action="store_true",
        help="Also run seed_demo before repair (creates demo humans if missing)",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON only")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        ensure_genesis_entities(db)
        ensure_pocp_org_foundation(db)
        repair_result: dict | None = None
        if args.full_seed:
            seed_demo(db)
        elif args.repair:
            repair_result = ensure_platform_entity_catalog(db)
        db.commit()

        audit = audit_entity_catalog(db)
        if args.json:
            print(json.dumps({"repair": repair_result, "audit": audit}, indent=2))
        else:
            print("=== Entity Catalog Audit ===")
            print(f"Entities: {audit['entity_count']} ({audit['ontology_type_count']} ontology types)")
            print(f"By type: {json.dumps(audit['by_type'], ensure_ascii=False)}")
            if audit["missing_types"]:
                print(f"Missing types: {', '.join(audit['missing_types'])}")
            else:
                print("All ontology entity types represented.")
            print(f"Capabilities: {audit['capability_count']}")
            if audit["missing_capabilities"]:
                print(f"Missing capabilities: {', '.join(audit['missing_capabilities'])}")
            if audit["missing_infrastructure_ids"]:
                print(f"Missing infrastructure: {', '.join(audit['missing_infrastructure_ids'])}")
            if audit["unassigned_demo_entities"]:
                print(f"Unassigned demo entities: {len(audit['unassigned_demo_entities'])}")
            if repair_result and not repair_result.get("skipped"):
                print("\n=== Repair Actions ===")
                print(f"Infrastructure created: {repair_result.get('infrastructure_created', [])}")
                print(f"Capabilities created: {repair_result.get('capabilities_created', [])}")
                print(f"Ownership assigned: {len(repair_result.get('ownership_assigned', []))}")
            print(f"\nComplete: {audit['complete']}")
        return 0 if audit["complete"] else 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
