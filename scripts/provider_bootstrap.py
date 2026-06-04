#!/usr/bin/env python3
"""CIP-P2.3 — Bootstrap a capability provider from a YAML manifest.

Flow: YAML manifest → Entity + registry capabilities → public directory → quote probe.

Usage:
  python scripts/provider_bootstrap.py
  python scripts/provider_bootstrap.py docs/public-node/examples/provider.manifest.example.yaml
  python scripts/provider_bootstrap.py --verify-url http://127.0.0.1:8000 --quote
  python scripts/provider_bootstrap.py --json
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
DEFAULT_MANIFEST = REPO_ROOT / "docs/public-node/examples/provider.manifest.example.yaml"
PROVIDER_MANIFEST_SCHEMA = "pocp.provider_manifest.v0.1"

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(BACKEND_ROOT / ".env", override=False)
except ImportError:
    pass


def load_manifest(path: Path) -> dict[str, Any]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"Manifest must be a YAML mapping: {path}")
    schema = raw.get("schema")
    if schema != PROVIDER_MANIFEST_SCHEMA:
        raise ValueError(f"Unsupported schema {schema!r}; expected {PROVIDER_MANIFEST_SCHEMA}")
    provider = raw.get("provider") or {}
    if not provider.get("name"):
        raise ValueError("provider.name is required")
    if not provider.get("entity_type"):
        raise ValueError("provider.entity_type is required")
    caps = raw.get("capabilities") or []
    if not caps:
        raise ValueError("capabilities must contain at least one entry")
    for idx, cap in enumerate(caps):
        if not cap.get("capability_type"):
            raise ValueError(f"capabilities[{idx}].capability_type is required")
        if not cap.get("name"):
            raise ValueError(f"capabilities[{idx}].name is required")
        if not cap.get("unit"):
            raise ValueError(f"capabilities[{idx}].unit is required")
    return raw


def _ensure_billing_anchor(db, entity_id: str) -> None:
    from genesis import RAIN_ID, ensure_genesis_entities
    from models.entity import Entity
    from services.contribution import grant_registration_credits
    from services.org_foundation import ensure_pocp_org_foundation

    ensure_genesis_entities(db)
    ensure_pocp_org_foundation(db)
    entity = db.get(Entity, entity_id)
    if entity is None and entity_id == RAIN_ID:
        from models.entity import EntityStatus, EntityType

        entity = Entity(
            id=RAIN_ID,
            entity_type=EntityType.human,
            name="Rain",
            description="Platform founder and contributor",
            status=EntityStatus.active,
        )
        db.add(entity)
        db.flush()
    if entity is None:
        raise ValueError(f"quote_test.from_entity_id not found: {entity_id}")
    grant_registration_credits(db, entity)


def bootstrap_provider(db, manifest: dict[str, Any]) -> dict[str, Any]:
    from genesis import RAIN_ID, ensure_genesis_entities
    from models.capability import EntityCapability
    from models.entity import Entity
    from services.capability.registry import register_capability
    from services.entity_register import register_entity
    from services.org_foundation import ensure_pocp_org_foundation

    ensure_genesis_entities(db)
    ensure_pocp_org_foundation(db)

    provider = manifest["provider"]
    entity_id = provider.get("entity_id")
    owner_id = provider.get("owner_id") or RAIN_ID
    _ensure_billing_anchor(db, owner_id)

    entity = db.get(Entity, entity_id) if entity_id else None
    created_entity = False
    if entity is None:
        metadata = dict(provider.get("metadata") or {})
        portable_id = provider.get("portable_id")
        if portable_id:
            metadata["portable_id"] = portable_id
        entity = register_entity(
            db,
            entity_id=entity_id,
            entity_type=provider["entity_type"],
            name=provider["name"],
            description=provider.get("description"),
            owner_id=owner_id,
            creator_id=owner_id,
            metadata=metadata or None,
        )
        created_entity = True
        entity_id = entity.id

    capabilities_created: list[str] = []
    capabilities_existing: list[str] = []
    for cap in manifest["capabilities"]:
        cap_id = cap.get("capability_id")
        if cap_id and db.get(EntityCapability, cap_id):
            capabilities_existing.append(cap_id)
            continue
        record = register_capability(
            db,
            entity_id=entity_id,
            capability_id=cap_id,
            capability_type=cap["capability_type"],
            name=cap["name"],
            unit=cap["unit"],
            price_model=cap.get("price_model", "fixed"),
            base_price=float(cap.get("base_price", 0.0)),
            accepted_units=cap.get("accepted_units"),
            verification_method=cap.get("verification_method", "human_review"),
            availability=cap.get("availability", "available"),
            reputation_score=float(cap.get("reputation_score", 0.0)),
            risk_level=cap.get("risk_level", "low"),
            metadata=cap.get("metadata"),
        )
        capabilities_created.append(record.id)

    return {
        "entity_id": entity_id,
        "entity_created": created_entity,
        "capabilities_created": capabilities_created,
        "capabilities_existing": capabilities_existing,
    }


def verify_directory(db, entity_id: str, *, capability_type: str | None = None) -> tuple[bool, str]:
    from services.node_manifest import list_provider_directory

    listing = list_provider_directory(db, capability_type=capability_type, limit=500)
    matches = [
        item
        for item in listing.get("items") or []
        if item.get("provider_entity_id") == entity_id
    ]
    if matches:
        return True, f"directory lists {len(matches)} offer(s) for {entity_id}"
    return False, f"provider {entity_id} not found in GET /api/v1/capabilities/directory"


def verify_directory_http(base_url: str, entity_id: str) -> tuple[bool, str]:
    import urllib.error
    import urllib.request

    url = f"{base_url.rstrip('/')}/api/v1/capabilities/directory?limit=200"
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            listing = json.loads(response.read().decode())
    except urllib.error.URLError as exc:
        return False, f"HTTP directory fetch failed: {exc.reason}"

    matches = [
        item
        for item in listing.get("items") or []
        if item.get("provider_entity_id") == entity_id
    ]
    if matches:
        return True, f"HTTP directory lists {len(matches)} offer(s) for {entity_id}"
    return False, f"provider {entity_id} not found at {url}"


def verify_quote(db, manifest: dict[str, Any], entity_id: str) -> tuple[bool, str]:
    from services.entity_dialogue import ENTITY_DIALOGUE_SCHEMA, _handle_quote

    quote_cfg = manifest.get("quote_test") or {}
    from_entity_id = quote_cfg.get("from_entity_id")
    if not from_entity_id:
        return True, "quote_test skipped (no from_entity_id)"

    _ensure_billing_anchor(db, from_entity_id)

    envelope = {
        "schema": ENTITY_DIALOGUE_SCHEMA,
        "dialogue_id": f"dlg_provider_bootstrap_{uuid.uuid4().hex[:12]}",
        "kind": "quote",
        "from": {"entity_id": from_entity_id},
        "to": {"entity_id": entity_id},
        "payload": {
            "quote_action": quote_cfg.get("quote_action", "capability_invoke"),
            "estimated_cost": float(quote_cfg.get("estimated_cost", 5.0)),
        },
    }
    response = _handle_quote(db, envelope)
    status = response.get("status")
    if status != "accepted":
        errors = response.get("errors") or []
        return False, f"quote rejected: {errors or response}"

    result = response.get("result") or {}
    quote = result.get("quote") or {}
    if quote.get("allowed") is not True:
        return False, f"quote not allowed: {quote}"
    refs = response.get("refs") or {}
    exchange_id = result.get("exchange_id") or refs.get("exchange_id")
    return True, f"quote accepted (exchange_id={exchange_id}, cost={quote.get('cost')})"


def run_bootstrap(
    manifest_path: Path,
    *,
    verify_url: str | None = None,
    run_quote: bool = False,
) -> dict[str, Any]:
    from database import SessionLocal

    manifest = load_manifest(manifest_path)
    db = SessionLocal()
    try:
        bootstrap = bootstrap_provider(db, manifest)
        db.commit()

        entity_id = bootstrap["entity_id"]
        checks: dict[str, Any] = {}

        ok_dir, detail_dir = verify_directory(db, entity_id)
        checks["directory"] = {"ok": ok_dir, "detail": detail_dir}

        if verify_url:
            ok_http, detail_http = verify_directory_http(verify_url, entity_id)
            checks["directory_http"] = {"ok": ok_http, "detail": detail_http}

        if run_quote or manifest.get("quote_test"):
            ok_quote, detail_quote = verify_quote(db, manifest, entity_id)
            checks["quote"] = {"ok": ok_quote, "detail": detail_quote}

        valid = all(check.get("ok") for check in checks.values())
        return {
            "valid": valid,
            "manifest": str(manifest_path),
            "bootstrap": bootstrap,
            "checks": checks,
        }
    finally:
        db.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Bootstrap a PoCP provider from YAML manifest")
    parser.add_argument(
        "manifest",
        nargs="?",
        default=str(DEFAULT_MANIFEST),
        help=f"Path to provider manifest YAML (default: {DEFAULT_MANIFEST.relative_to(REPO_ROOT)})",
    )
    parser.add_argument(
        "--verify-url",
        metavar="URL",
        help="Also verify provider appears in live GET /api/v1/capabilities/directory",
    )
    parser.add_argument(
        "--quote",
        action="store_true",
        help="Run entity dialogue quote probe after bootstrap",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON result only")
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    if not manifest_path.is_file():
        print(f"Manifest not found: {manifest_path}", file=sys.stderr)
        return 1

    try:
        result = run_bootstrap(
            manifest_path,
            verify_url=args.verify_url,
            run_quote=args.quote,
        )
    except ValueError as exc:
        print(json.dumps({"valid": False, "error": str(exc)}, indent=2), file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print("=== Provider Bootstrap (CIP-P2.3) ===")
        print(f"Manifest: {result['manifest']}")
        boot = result["bootstrap"]
        print(f"Entity: {boot['entity_id']} ({'created' if boot['entity_created'] else 'existing'})")
        print(f"Capabilities created: {boot['capabilities_created'] or 'none'}")
        if boot["capabilities_existing"]:
            print(f"Capabilities existing: {boot['capabilities_existing']}")
        print("\n=== Checks ===")
        for name, check in result["checks"].items():
            status = "PASS" if check["ok"] else "FAIL"
            print(f"{name}: {status} — {check['detail']}")
        print(f"\nValid: {result['valid']}")

    return 0 if result.get("valid") else 1


if __name__ == "__main__":
    raise SystemExit(main())
