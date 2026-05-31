"""Entity market pricing — market_profile overrides + capability registry base_price."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from models.entity import Entity
from services.capability.registry import search_capabilities

MARKET_PROFILE_KEY = "market_profile"


def get_market_profile(entity: Entity | None) -> dict[str, Any] | None:
    if entity is None:
        return None
    meta = entity.metadata_ or {}
    profile = meta.get(MARKET_PROFILE_KEY)
    return profile if isinstance(profile, dict) else None


def validate_market_profile(profile: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(profile, dict):
        raise ValueError("market_profile must be an object")
    overrides = profile.get("overrides") or {}
    if not isinstance(overrides, dict):
        raise ValueError("market_profile.overrides must be an object")
    normalized: dict[str, Any] = {}
    for key, value in overrides.items():
        if not isinstance(value, dict):
            continue
        entry: dict[str, Any] = {}
        if "provider_per_1k_total" in value:
            entry["provider_per_1k_total"] = float(value["provider_per_1k_total"])
        if "consumer_per_1k_prompt" in value:
            entry["consumer_per_1k_prompt"] = float(value["consumer_per_1k_prompt"])
        if "consumer_per_1k_completion" in value:
            entry["consumer_per_1k_completion"] = float(value["consumer_per_1k_completion"])
        if "provider_tokens" in value:
            entry["provider_tokens"] = float(value["provider_tokens"])
        if "consumer_tokens" in value:
            entry["consumer_tokens"] = float(value["consumer_tokens"])
        if entry:
            normalized[str(key)] = entry
    return {
        "spec_version": str(profile.get("spec_version") or "0.2"),
        "pricing_mode": str(profile.get("pricing_mode") or "protocol_default"),
        "overrides": normalized,
    }


def register_market_profile(
    db: Session,
    entity_id: str,
    profile: dict[str, Any],
) -> dict[str, Any]:
    entity = db.get(Entity, entity_id)
    if entity is None:
        raise ValueError(f"Entity not found: {entity_id}")
    normalized = validate_market_profile(profile)
    meta = dict(entity.metadata_ or {})
    meta[MARKET_PROFILE_KEY] = normalized
    entity.metadata_ = meta
    db.flush()
    return normalized


def _override_keys(capability: str, model: str | None) -> list[str]:
    keys = []
    if model:
        keys.append(f"{capability}:{model}")
    keys.append(capability)
    return keys


def resolve_rate_overrides(
    db: Session | None,
    *,
    provider_entity_id: str | None,
    capability: str,
    model: str | None = None,
) -> dict[str, float]:
    """Merge market_profile overrides for a provider Entity."""
    if not db or not provider_entity_id:
        return {}
    entity = db.get(Entity, provider_entity_id)
    mp = get_market_profile(entity)
    if not mp:
        return {}
    overrides = mp.get("overrides") or {}
    for key in _override_keys(capability, model):
        entry = overrides.get(key)
        if isinstance(entry, dict):
            return {k: float(v) for k, v in entry.items() if isinstance(v, (int, float))}
    return {}


def resolve_intel_listing_price(
    db: Session | None,
    *,
    provider_entity_id: str,
    service: str,
) -> tuple[float | None, float | None]:
    """Return (consumer_tokens, provider_tokens) from capability registry if listed."""
    if not db:
        return None, None
    unit_map = {
        "witness": "skill_invocation",
        "matching": "skill_invocation",
        "skill_invocation": "skill_invocation",
        "agent_run": "agent_run",
    }
    unit = unit_map.get(service, "skill_invocation")
    rows = search_capabilities(db, entity_id=provider_entity_id, limit=20)
    for row in rows:
        if row.unit.value == unit or row.capability_type.value in (service, "coding", "reasoning", "review"):
            price = float(row.base_price or 0)
            if price <= 0:
                continue
            if row.price_model.value == "sponsored":
                return 0.0, price
            return price, price
    return None, None
