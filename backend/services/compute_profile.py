"""ComputeProfile — Entity-attached distributed compute declaration (v0.1)."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from models.entity import Entity, EntityStatus
from services.compute_mesh import (
    mesh_scope_label,
    normalize_mesh_policy,
    provider_visible_to_initiator,
    resolve_org_entity_id,
)

COMPUTE_PROFILE_KEY = "compute_profile"
COMPUTE_PROFILE_SPEC = "0.1"
DEFAULT_HEARTBEAT_STALE_SECONDS = int(os.getenv("POCP_COMPUTE_HEARTBEAT_STALE_SECONDS", "900"))

VALID_CAPABILITIES = frozenset(
    {
        "llm_inference",
        "embeddings",
        "witness",
        "mcp_host",
        "agent_runtime",
    }
)
VALID_STATUSES = frozenset({"active", "idle", "offline"})


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_iso(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        text = ts.replace("Z", "+00:00")
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def is_profile_stale(profile: dict[str, Any], *, stale_seconds: int | None = None) -> bool:
    stale_seconds = stale_seconds or DEFAULT_HEARTBEAT_STALE_SECONDS
    last = _parse_iso(profile.get("last_heartbeat"))
    if last is None:
        return False
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    age = (datetime.now(timezone.utc) - last).total_seconds()
    return age > stale_seconds


def refresh_provider_liveness(db: Session, *, stale_seconds: int | None = None) -> int:
    """Mark active profiles offline when heartbeat is stale."""
    stale_seconds = stale_seconds or DEFAULT_HEARTBEAT_STALE_SECONDS
    updated = 0
    for entity in db.query(Entity).all():
        profile = get_compute_profile(entity)
        if not profile or profile.get("status") != "active":
            continue
        if not is_profile_stale(profile, stale_seconds=stale_seconds):
            continue
        patched = dict(profile)
        patched["status"] = "offline"
        patched["stale_reason"] = "heartbeat_timeout"
        meta = dict(entity.metadata_ or {})
        meta[COMPUTE_PROFILE_KEY] = patched
        entity.metadata_ = meta
        updated += 1
    if updated:
        db.flush()
    return updated


def validate_compute_profile(profile: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(profile, dict):
        raise ValueError("compute_profile must be an object")

    offers = profile.get("offers") or []
    if not offers:
        raise ValueError("compute_profile.offers must be a non-empty list")

    normalized_offers: list[dict[str, Any]] = []
    for offer in offers:
        if not isinstance(offer, dict):
            raise ValueError("each offer must be an object")
        capability = str(offer.get("capability") or "").strip()
        if capability not in VALID_CAPABILITIES:
            raise ValueError(
                f"invalid capability {capability!r}; "
                f"must be one of: {', '.join(sorted(VALID_CAPABILITIES))}"
            )
        normalized_offers.append(
            {
                "capability": capability,
                "models": list(offer.get("models") or []),
                "adapters": list(offer.get("adapters") or []),
                "tools": list(offer.get("tools") or []),
            }
        )

    endpoints = profile.get("endpoints") or {}
    if not isinstance(endpoints, dict):
        raise ValueError("compute_profile.endpoints must be an object")

    status = str(profile.get("status") or "active").strip()
    if status not in VALID_STATUSES:
        raise ValueError(f"status must be one of: {', '.join(sorted(VALID_STATUSES))}")

    policy = profile.get("policy") or {}
    capacity = profile.get("capacity") or {}
    accountability = profile.get("accountability") or {}
    normalized_policy = normalize_mesh_policy({"policy": policy})

    return {
        "spec_version": COMPUTE_PROFILE_SPEC,
        "offers": normalized_offers,
        "endpoints": {
            "base_url": str(endpoints.get("base_url") or "").strip(),
            "witness": str(endpoints.get("witness") or "/api/v1/intelligence/compute/witness"),
            "status": str(endpoints.get("status") or "/api/v1/intelligence/compute/status"),
            "mcp_invoke": str(endpoints.get("mcp_invoke") or "/api/v1/intelligence/compute/mcp/invoke"),
        },
        "capacity": {
            "max_concurrent": int(capacity.get("max_concurrent") or 1),
            "region": str(capacity.get("region") or ""),
        },
        "accountability": {
            "owner_entity_id": accountability.get("owner_entity_id"),
        },
        "policy": {
            "accepts_public_jobs": bool(normalized_policy.get("accepts_public_jobs", False)),
            "visibility": normalized_policy["visibility"],
            "trusted_node_ids": list(normalized_policy.get("trusted_node_ids") or []),
            "organization_entity_id": normalized_policy.get("organization_entity_id"),
            "min_public_reputation": float(
                normalized_policy.get("min_public_reputation", 0.5)
            ),
        },
        "status": status,
        "registered_at": profile.get("registered_at") or _now_iso(),
        "last_heartbeat": profile.get("last_heartbeat") or _now_iso(),
    }


def get_compute_profile(entity: Entity) -> dict[str, Any] | None:
    meta = entity.metadata_ or {}
    profile = meta.get(COMPUTE_PROFILE_KEY)
    return profile if isinstance(profile, dict) else None


def entity_offers_capability(entity: Entity, capability: str) -> bool:
    profile = get_compute_profile(entity)
    if not profile or profile.get("status") != "active":
        return False
    return any(o.get("capability") == capability for o in profile.get("offers") or [])


def register_compute_profile(
    db: Session,
    entity_id: str,
    profile: dict[str, Any],
    *,
    owner_entity_id: str | None = None,
) -> Entity:
    entity = db.get(Entity, entity_id)
    if entity is None:
        raise HTTPException(status_code=404, detail="Entity not found")

    if owner_entity_id and entity.owner_id and entity.owner_id != owner_entity_id:
        raise HTTPException(status_code=403, detail="Not authorized to register compute on this entity")

    normalized = validate_compute_profile(profile)
    if not normalized["accountability"].get("owner_entity_id"):
        normalized["accountability"]["owner_entity_id"] = owner_entity_id or entity.owner_id or entity.id

    meta = dict(entity.metadata_ or {})
    meta[COMPUTE_PROFILE_KEY] = normalized
    meta["contribution_capable"] = meta.get("contribution_capable", True)
    entity.metadata_ = meta
    db.flush()
    return entity


def heartbeat_compute_profile(
    db: Session,
    entity_id: str,
    *,
    status: str = "active",
    owner_entity_id: str | None = None,
) -> Entity:
    entity = db.get(Entity, entity_id)
    if entity is None:
        raise HTTPException(status_code=404, detail="Entity not found")
    if owner_entity_id and entity.owner_id and entity.owner_id != owner_entity_id:
        raise HTTPException(status_code=403, detail="Not authorized to update compute profile")
    profile = get_compute_profile(entity)
    if profile is None:
        raise HTTPException(status_code=404, detail="Entity has no compute_profile")
    if status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"status must be one of: {', '.join(sorted(VALID_STATUSES))}")

    updated = dict(profile)
    updated["status"] = status
    updated["last_heartbeat"] = _now_iso()
    meta = dict(entity.metadata_ or {})
    meta[COMPUTE_PROFILE_KEY] = updated
    entity.metadata_ = meta
    db.flush()
    return entity


def list_compute_provider_entities(
    db: Session,
    *,
    capability: str | None = None,
    status: str = "active",
    refresh_liveness: bool = True,
    initiator_entity_id: str | None = None,
    organization_entity_id: str | None = None,
    mesh_filter: bool = True,
) -> list[dict[str, Any]]:
    if refresh_liveness:
        refresh_provider_liveness(db)
    entities = db.query(Entity).filter(Entity.status == EntityStatus.active).all()
    out: list[dict[str, Any]] = []
    for entity in entities:
        profile = get_compute_profile(entity)
        if not profile:
            continue
        if status and profile.get("status") != status:
            continue
        if capability and not entity_offers_capability(entity, capability):
            continue
        if organization_entity_id:
            policy_org = (profile.get("policy") or {}).get("organization_entity_id")
            provider_org = policy_org or resolve_org_entity_id(db, entity.id)
            if provider_org != organization_entity_id:
                continue
        if mesh_filter and initiator_entity_id and not provider_visible_to_initiator(
            db,
            provider=entity,
            profile=profile,
            initiator_entity_id=initiator_entity_id,
        ):
            continue
        scope = mesh_scope_label(
            db,
            provider=entity,
            profile=profile,
            initiator_entity_id=initiator_entity_id,
        )
        out.append(
            {
                "entity_id": entity.id,
                "entity_type": entity.entity_type.value,
                "name": entity.name,
                "compute_profile": profile,
                "mesh_scope": scope,
                "organization_entity_id": resolve_org_entity_id(db, entity.id),
            }
        )
    out.sort(key=lambda row: row["name"].lower())
    return out
