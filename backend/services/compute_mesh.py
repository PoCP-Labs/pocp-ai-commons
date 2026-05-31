"""Org-scoped compute mesh visibility — Phase δ (no public DHT)."""

from __future__ import annotations

import os
from typing import Any

from sqlalchemy.orm import Session

from models.entity import Entity, EntityType
from services.compute_reputation import get_compute_provider_reputation
from services.trust_config import load_trusted_nodes

VISIBILITY_ORG_ONLY = "org_only"
VISIBILITY_TRUSTED = "trusted_federation"
VISIBILITY_PUBLIC = "public_vouched"

VALID_VISIBILITIES = frozenset({VISIBILITY_ORG_ONLY, VISIBILITY_TRUSTED, VISIBILITY_PUBLIC})
DEFAULT_MIN_PUBLIC_REPUTATION = float(os.getenv("POCP_COMPUTE_PUBLIC_MIN_REPUTATION", "0.5"))


def local_node_id() -> str:
    return os.getenv("POCP_NODE_ID", "pocp-node-local").strip()


def resolve_org_entity_id(db: Session, entity_id: str | None) -> str | None:
    if not entity_id:
        return None
    entity = db.get(Entity, entity_id)
    if entity is None:
        return None

    meta = entity.metadata_ or {}
    org_id = meta.get("org_entity_id")
    if org_id:
        return str(org_id)

    if entity.entity_type == EntityType.organization:
        return entity.id

    if entity.owner_id:
        owner = db.get(Entity, entity.owner_id)
        if owner and owner.entity_type == EntityType.organization:
            return owner.id

    return None


def normalize_mesh_policy(profile: dict[str, Any]) -> dict[str, Any]:
    policy = dict(profile.get("policy") or {})
    accepts_public = bool(policy.get("accepts_public_jobs", False))
    visibility = str(policy.get("visibility") or "").strip()
    if visibility not in VALID_VISIBILITIES:
        visibility = VISIBILITY_PUBLIC if accepts_public else VISIBILITY_ORG_ONLY
    policy["visibility"] = visibility
    policy.setdefault("trusted_node_ids", [])
    policy.setdefault("organization_entity_id", None)
    policy.setdefault("min_public_reputation", DEFAULT_MIN_PUBLIC_REPUTATION)
    return policy


def _same_org(db: Session, a_id: str | None, b_id: str | None) -> bool:
    if not a_id or not b_id:
        return False
    org_a = resolve_org_entity_id(db, a_id)
    org_b = resolve_org_entity_id(db, b_id)
    return bool(org_a and org_b and org_a == org_b)


def _owner_affinity(db: Session, provider: Entity, profile: dict[str, Any], initiator_id: str) -> bool:
    initiator = db.get(Entity, initiator_id)
    if initiator is None:
        return False
    owner_id = (profile.get("accountability") or {}).get("owner_entity_id")
    if owner_id and owner_id == initiator_id:
        return True
    if provider.owner_id == initiator_id:
        return True
    if initiator.owner_id and provider.id == initiator.owner_id:
        return True
    if initiator.owner_id and provider.owner_id == initiator.owner_id:
        return True
    policy_org = (profile.get("policy") or {}).get("organization_entity_id")
    initiator_org = resolve_org_entity_id(db, initiator_id)
    if policy_org and initiator_org and str(policy_org) == initiator_org:
        return True
    return _same_org(db, provider.id, initiator_id) or _same_org(db, owner_id, initiator_id)


def _trusted_federation_allowed(profile: dict[str, Any], node_id: str) -> bool:
    policy = profile.get("policy") or {}
    trusted_ids = {str(x) for x in policy.get("trusted_node_ids") or []}
    if node_id in trusted_ids:
        return True
    federation_ids = {n.node_id for n in load_trusted_nodes()}
    return bool(trusted_ids & federation_ids)


def provider_visible_to_initiator(
    db: Session,
    *,
    provider: Entity,
    profile: dict[str, Any],
    initiator_entity_id: str | None,
    node_id: str | None = None,
) -> bool:
    """Mesh visibility gate — org-scoped by default."""
    policy = normalize_mesh_policy(profile)
    visibility = policy["visibility"]
    node_id = node_id or local_node_id()

    if not initiator_entity_id:
        if visibility == VISIBILITY_PUBLIC and policy.get("accepts_public_jobs"):
            rep = get_compute_provider_reputation(db, provider.id)
            return rep >= float(policy.get("min_public_reputation", DEFAULT_MIN_PUBLIC_REPUTATION))
        return visibility in (VISIBILITY_TRUSTED, VISIBILITY_PUBLIC) and policy.get(
            "accepts_public_jobs", False
        )

    if _owner_affinity(db, provider, profile, initiator_entity_id):
        return True

    if visibility == VISIBILITY_ORG_ONLY:
        return False

    if visibility == VISIBILITY_TRUSTED:
        return _trusted_federation_allowed(profile, node_id)

    if visibility == VISIBILITY_PUBLIC:
        if not policy.get("accepts_public_jobs"):
            return False
        rep = get_compute_provider_reputation(db, provider.id)
        min_rep = float(policy.get("min_public_reputation", DEFAULT_MIN_PUBLIC_REPUTATION))
        if rep >= min_rep:
            return True
        return _trusted_federation_allowed(profile, node_id)

    return False


def mesh_scope_label(
    db: Session,
    *,
    provider: Entity,
    profile: dict[str, Any],
    initiator_entity_id: str | None,
) -> str:
    policy = normalize_mesh_policy(profile)
    if initiator_entity_id and _owner_affinity(db, provider, profile, initiator_entity_id):
        return "org_affinity"
    visibility = policy["visibility"]
    if visibility == VISIBILITY_ORG_ONLY:
        return "org_only"
    if visibility == VISIBILITY_TRUSTED:
        return "trusted_federation"
    return "public_vouched"
