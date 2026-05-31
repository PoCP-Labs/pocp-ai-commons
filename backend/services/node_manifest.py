"""Entity node manifest — capability-first provider/consumer facets."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from models.capability import CapabilityType, EntityCapability
from models.entity import Entity, EntityStatus, EntityType
from models.wallet import Wallet
from services.capability.registry import descriptor_from_record
from services.compute_profile import get_compute_profile
from services.exchange_spine import COMPUTE_CAPABILITIES
from services.federation_community import local_federation_entity_id
from services.org_foundation import POCP_ORG_NAME

MANIFEST_PROTOCOL = "pocp-node-manifest-v0.2-capability-first"

COMPUTE_CAPABILITY_TYPES = frozenset(
    {
        CapabilityType.gpu_inference.value,
        CapabilityType.gpu_training.value,
        "gpu_inference",
        "gpu_training",
        "embeddings",
        "training",
    }
)

WITNESS_ROLES = frozenset(
    {
        "ai_witness_node",
        "witness",
        "genesis_ai_collaborator",
    }
)


def _backend_url() -> str:
    return os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")


def _instance_id() -> str:
    return os.getenv("POCP_NODE_ID", "pocp-node-local")


def _exchange_kind_for_capability(capability_type: str) -> str:
    cap = (capability_type or "").lower()
    if cap in COMPUTE_CAPABILITIES or cap in COMPUTE_CAPABILITY_TYPES or cap == "llm_inference":
        return "compute"
    return "capability"


def _capability_unit_default(capability_type: str) -> str:
    if _exchange_kind_for_capability(capability_type) == "compute":
        return "gpu_second"
    if capability_type in ("tool_call",):
        return "mcp_tool_call"
    if capability_type in ("reasoning", "coding", "review", "general"):
        return "skill_invocation"
    return "llm_token"


def _entity_capabilities(db: Session, entity_id: str) -> list[dict[str, Any]]:
    rows = (
        db.query(EntityCapability)
        .filter(EntityCapability.entity_id == entity_id)
        .order_by(EntityCapability.created_at.asc())
        .all()
    )
    items: list[dict[str, Any]] = []
    for row in rows:
        desc = descriptor_from_record(row)
        cap_type = desc.capability_type
        items.append(
            {
                "capability_id": desc.capability_id,
                "capability_type": cap_type,
                "name": desc.name,
                "unit": desc.unit,
                "exchange_kind": _exchange_kind_for_capability(cap_type),
                "base_price": desc.base_price,
                "price_model": desc.price_model,
                "availability": desc.availability,
                "accepted_units": desc.accepted_units,
            }
        )
    return items


def _compute_profile_capabilities(entity: Entity) -> list[dict[str, Any]]:
    profile = get_compute_profile(entity)
    if not profile:
        return []
    items: list[dict[str, Any]] = []
    for offer in profile.get("offers") or []:
        if isinstance(offer, str):
            cap = offer
            adapters: list[str] = []
        else:
            cap = str(offer.get("capability") or offer.get("name") or "llm_inference")
            adapters = offer.get("adapters") or []
        items.append(
            {
                "capability_type": cap,
                "name": cap.replace("_", " ").title(),
                "unit": "gpu_second" if cap in COMPUTE_CAPABILITIES else "llm_token",
                "exchange_kind": _exchange_kind_for_capability(cap),
                "adapters": adapters,
                "source": "compute_profile",
            }
        )
    return items


def resolve_entity_facets(db: Session, entity: Entity) -> list[str]:
    facets: list[str] = []
    wallet = db.query(Wallet).filter(Wallet.entity_id == entity.id).first()
    if wallet:
        facets.append("consumer")

    profile = get_compute_profile(entity)
    if profile and (profile.get("offers") or profile.get("capabilities")):
        facets.append("compute_provider")

    caps = _entity_capabilities(db, entity.id)
    meta_caps = (entity.metadata_ or {}).get("capabilities") or []
    if caps or meta_caps:
        facets.append("capability_provider")

    roles = set((entity.metadata_ or {}).get("roles") or [])
    if roles & WITNESS_ROLES:
        facets.append("witness")

    if entity.entity_type in (EntityType.organization, EntityType.community):
        if "federation_node" in roles or entity.name == POCP_ORG_NAME:
            facets.append("instance_host")

    if entity.id == local_federation_entity_id():
        facets.append("instance_host")

    return facets


def build_entity_node_manifest(db: Session, entity_id: str) -> dict[str, Any]:
    entity = db.get(Entity, entity_id)
    if not entity:
        raise ValueError(f"Entity not found: {entity_id}")

    backend = _backend_url()
    facets = resolve_entity_facets(db, entity)
    registry_caps = _entity_capabilities(db, entity.id)
    compute_caps = _compute_profile_capabilities(entity)

    capabilities: list[dict[str, Any]] = list(registry_caps)
    seen_types = {c.get("capability_type") for c in capabilities}
    for item in compute_caps:
        if item["capability_type"] not in seen_types:
            capabilities.append(item)

    profile = get_compute_profile(entity)
    endpoints: dict[str, str] = {
        "manifest": f"{backend}/api/v1/entities/{entity.id}/node-manifest",
        "entity": f"{backend}/api/v1/entities/{entity.id}",
    }
    if "capability_provider" in facets or entity.entity_type in (
        EntityType.skill,
        EntityType.agent,
        EntityType.tool,
    ):
        endpoints["capabilities"] = f"{backend}/api/v1/registry/capabilities?entity_id={entity.id}"
    if "compute_provider" in facets or profile:
        endpoints["compute_register"] = f"{backend}/api/v1/compute/entities/{entity.id}/register"

    manifest: dict[str, Any] = {
        "protocol": MANIFEST_PROTOCOL,
        "kind": "entity",
        "entity_id": entity.id,
        "entity_type": entity.entity_type.value,
        "display_name": entity.name,
        "description": entity.description,
        "status": entity.status.value,
        "facets": facets,
        "capabilities": capabilities,
        "endpoints": endpoints,
        "wallet_id": None,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    wallet = db.query(Wallet).filter(Wallet.entity_id == entity.id).first()
    if wallet:
        manifest["wallet_id"] = wallet.id

    meta = entity.metadata_ or {}
    if meta.get("portable_id"):
        manifest["portable_id"] = meta["portable_id"]
    if meta.get("roles"):
        manifest["roles"] = meta["roles"]

    if "witness" in facets:
        manifest["witness"] = {
            "supported_evidence": ["capability_receipt.v0.1", "contribution.v0.3"],
        }

    if profile:
        manifest["compute_profile"] = {
            "status": profile.get("status"),
            "visibility": (profile.get("policy") or {}).get("visibility"),
            "last_heartbeat": profile.get("last_heartbeat"),
        }

    return manifest


def build_instance_node_manifest(db: Session) -> dict[str, Any]:
    backend = _backend_url()
    org = db.query(Entity).filter(Entity.name == POCP_ORG_NAME).first()
    archive_entity_id = org.id if org else local_federation_entity_id()

    return {
        "protocol": MANIFEST_PROTOCOL,
        "kind": "instance",
        "instance_id": _instance_id(),
        "display_name": os.getenv("POCP_INSTANCE_NAME", "PoCP AI Commons"),
        "facets": ["instance_host"],
        "archive_entity_id": archive_entity_id,
        "endpoints": {
            "well_known": f"{backend}/.well-known/pocp-node.json",
            "health": f"{backend}/health",
            "capabilities_directory": f"{backend}/api/v1/capabilities/directory",
            "ledger_verify": f"{backend}/api/v1/ledger/verify",
            "federation_node": f"{backend}/api/v1/federation/node",
        },
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


def list_provider_directory(
    db: Session,
    *,
    exchange_kind: str | None = None,
    capability_type: str | None = None,
    availability: str | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    """Public directory of compute + capability providers."""
    items: list[dict[str, Any]] = []
    seen: set[str] = set()

    cap_query = db.query(EntityCapability).join(Entity, Entity.id == EntityCapability.entity_id)
    cap_query = cap_query.filter(Entity.status == EntityStatus.active)
    if capability_type:
        cap_query = cap_query.filter(EntityCapability.capability_type == CapabilityType(capability_type))
    if availability:
        from models.capability import CapabilityAvailability

        cap_query = cap_query.filter(EntityCapability.availability == CapabilityAvailability(availability))

    for row in cap_query.order_by(EntityCapability.created_at.desc()).limit(limit * 2).all():
        entity = db.get(Entity, row.entity_id)
        if not entity:
            continue
        desc = descriptor_from_record(row)
        kind = _exchange_kind_for_capability(desc.capability_type)
        if exchange_kind and kind != exchange_kind:
            continue
        key = f"reg:{row.id}"
        if key in seen:
            continue
        seen.add(key)
        items.append(
            {
                "provider_entity_id": entity.id,
                "provider_name": entity.name,
                "provider_entity_type": entity.entity_type.value,
                "capability_id": desc.capability_id,
                "capability_type": desc.capability_type,
                "name": desc.name,
                "unit": desc.unit,
                "exchange_kind": kind,
                "base_price": desc.base_price,
                "price_model": desc.price_model,
                "availability": desc.availability,
                "source": "registry",
                "manifest_url": f"{_backend_url()}/api/v1/entities/{entity.id}/node-manifest",
            }
        )
        if len(items) >= limit:
            break

    if len(items) < limit and (exchange_kind in (None, "compute")):
        for entity in db.query(Entity).filter(Entity.status == EntityStatus.active).all():
            profile = get_compute_profile(entity)
            if not profile or profile.get("status") not in ("active", "idle"):
                continue
            for offer in _compute_profile_capabilities(entity):
                cap_t = offer["capability_type"]
                if capability_type and cap_t != capability_type:
                    continue
                key = f"compute:{entity.id}:{cap_t}"
                if key in seen:
                    continue
                seen.add(key)
                items.append(
                    {
                        "provider_entity_id": entity.id,
                        "provider_name": entity.name,
                        "provider_entity_type": entity.entity_type.value,
                        "capability_id": None,
                        "capability_type": cap_t,
                        "name": offer["name"],
                        "unit": offer["unit"],
                        "exchange_kind": "compute",
                        "base_price": None,
                        "price_model": "metered",
                        "availability": profile.get("status", "active"),
                        "source": "compute_profile",
                        "manifest_url": f"{_backend_url()}/api/v1/entities/{entity.id}/node-manifest",
                    }
                )
                if len(items) >= limit:
                    break
            if len(items) >= limit:
                break

    return {
        "spec_version": "0.2",
        "count": len(items),
        "items": items[:limit],
    }
