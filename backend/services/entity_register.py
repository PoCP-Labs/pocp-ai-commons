"""Typed Entity registration with ontology validation."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from intelligence.entity_ontology import (
    validate_entity_type,
    validate_participant_role,
)
from models.entity import Entity, EntityStatus, EntityType
from services.contribution import grant_registration_credits


def _parse_entity_type(entity_type: str) -> EntityType:
    validate_entity_type(entity_type)
    return EntityType(entity_type)


def _base_metadata(entity_type: str, extra: dict[str, Any] | None) -> dict[str, Any]:
    meta = dict(extra or {})
    meta.setdefault("registered_via", "entity_register")
    meta.setdefault("ontology_version", "0.3")
    meta.setdefault("entity_type_confirmed", entity_type)
    return meta


def register_entity(
    db: Session,
    *,
    entity_type: str,
    name: str,
    description: str | None,
    owner_id: str | None,
    creator_id: str | None,
    status: EntityStatus = EntityStatus.active,
    metadata: dict[str, Any] | None = None,
    entity_id: str | None = None,
) -> Entity:
    et = _parse_entity_type(entity_type)
    entity = Entity(
        entity_type=et,
        name=name.strip(),
        description=description,
        owner_id=owner_id,
        creator_id=creator_id or owner_id,
        status=status,
        metadata_=_base_metadata(entity_type, metadata),
    )
    if entity_id:
        entity.id = entity_id
    db.add(entity)
    db.flush()
    grant_registration_credits(db, entity)
    return entity


def register_tool(
    db: Session,
    *,
    name: str,
    description: str | None,
    maintainer_id: str,
    tool_kind: str = "mcp",
    service_endpoints: dict[str, str] | None = None,
    capabilities: list[str] | None = None,
    mcp_server: str | None = None,
    activate: bool = True,
    entity_id: str | None = None,
) -> Entity:
    metadata = {
        "tool_kind": tool_kind,
        "service_endpoints": service_endpoints or {},
        "capabilities": capabilities or [],
    }
    if mcp_server:
        metadata["mcp_server"] = mcp_server
    return register_entity(
        db,
        entity_type="tool",
        name=name,
        description=description,
        owner_id=maintainer_id,
        creator_id=maintainer_id,
        status=EntityStatus.active if activate else EntityStatus.pending,
        metadata=metadata,
        entity_id=entity_id,
    )


def register_dataset(
    db: Session,
    *,
    name: str,
    description: str | None,
    maintainer_id: str,
    source_uri: str | None = None,
    license: str | None = None,
    content_hash: str | None = None,
    data_format: str | None = None,
    activate: bool = True,
    entity_id: str | None = None,
) -> Entity:
    metadata = {
        "source_uri": source_uri,
        "license": license,
        "content_hash": content_hash,
        "format": data_format,
    }
    return register_entity(
        db,
        entity_type="dataset",
        name=name,
        description=description,
        owner_id=maintainer_id,
        creator_id=maintainer_id,
        status=EntityStatus.active if activate else EntityStatus.pending,
        metadata=metadata,
        entity_id=entity_id,
    )


def register_workflow(
    db: Session,
    *,
    name: str,
    description: str | None,
    maintainer_id: str,
    steps: list[dict[str, Any]] | None = None,
    version: str = "1.0.0",
    entrypoint: str | None = None,
    activate: bool = True,
    entity_id: str | None = None,
) -> Entity:
    metadata = {
        "steps": steps or [],
        "version": version,
        "entrypoint": entrypoint,
    }
    return register_entity(
        db,
        entity_type="workflow",
        name=name,
        description=description,
        owner_id=maintainer_id,
        creator_id=maintainer_id,
        status=EntityStatus.active if activate else EntityStatus.pending,
        metadata=metadata,
        entity_id=entity_id,
    )


def register_compute_node(
    db: Session,
    *,
    name: str,
    description: str | None,
    maintainer_id: str,
    region: str = "unknown",
    hardware: dict[str, Any] | None = None,
    capabilities: list[str] | None = None,
    verification_methods: list[str] | None = None,
    activate: bool = True,
    entity_id: str | None = None,
) -> Entity:
    metadata = {
        "compute_profile": {
            "region": region,
            "hardware": hardware or {},
            "capabilities": capabilities or [],
            "verification_methods": verification_methods or ["log"],
        },
        "region": region,
        "hardware": hardware or {},
        "capabilities": capabilities or [],
        "verification_methods": verification_methods or ["log"],
    }
    return register_entity(
        db,
        entity_type="compute_node",
        name=name,
        description=description,
        owner_id=maintainer_id,
        creator_id=maintainer_id,
        status=EntityStatus.active if activate else EntityStatus.pending,
        metadata=metadata,
        entity_id=entity_id,
    )


def register_verifier_node(
    db: Session,
    *,
    name: str,
    description: str | None,
    maintainer_id: str,
    verifier_kinds: list[str] | None = None,
    service_endpoints: dict[str, str] | None = None,
    trust_level: str = "standard",
    activate: bool = True,
    entity_id: str | None = None,
) -> Entity:
    metadata = {
        "verifier_kinds": verifier_kinds or ["ai_review"],
        "service_endpoints": service_endpoints or {},
        "trust_level": trust_level,
    }
    return register_entity(
        db,
        entity_type="verifier_node",
        name=name,
        description=description,
        owner_id=maintainer_id,
        creator_id=maintainer_id,
        status=EntityStatus.active if activate else EntityStatus.pending,
        metadata=metadata,
        entity_id=entity_id,
    )


def register_reviewer_node(
    db: Session,
    *,
    name: str,
    description: str | None,
    maintainer_id: str,
    review_policy: str = "human_review",
    queue_capacity: int = 50,
    supported_task_types: list[str] | None = None,
    activate: bool = True,
    entity_id: str | None = None,
) -> Entity:
    metadata = {
        "review_policy": review_policy,
        "queue_capacity": queue_capacity,
        "supported_task_types": supported_task_types or ["general"],
    }
    return register_entity(
        db,
        entity_type="reviewer_node",
        name=name,
        description=description,
        owner_id=maintainer_id,
        creator_id=maintainer_id,
        status=EntityStatus.active if activate else EntityStatus.pending,
        metadata=metadata,
        entity_id=entity_id,
    )


def register_sponsor_entity(
    db: Session,
    *,
    name: str,
    description: str | None,
    maintainer_id: str,
    sponsor_policy: str = "task_bounty",
    accepted_units: list[str] | None = None,
    activate: bool = True,
    entity_id: str | None = None,
) -> Entity:
    metadata = {
        "sponsor_policy": sponsor_policy,
        "accepted_units": accepted_units or ["AIC"],
        "pool_balance": 0.0,
    }
    return register_entity(
        db,
        entity_type="sponsor",
        name=name,
        description=description,
        owner_id=maintainer_id,
        creator_id=maintainer_id,
        status=EntityStatus.active if activate else EntityStatus.pending,
        metadata=metadata,
        entity_id=entity_id,
    )


def register_protocol_treasury(
    db: Session,
    *,
    name: str = "PoCP Protocol Treasury",
    description: str | None = None,
    governance_entity_id: str | None = None,
    fee_schedule: dict[str, Any] | None = None,
    entity_id: str | None = None,
) -> Entity:
    metadata = {
        "treasury_policy": "protocol_reserve",
        "fee_schedule": fee_schedule or {},
        "governance_entity_id": governance_entity_id,
    }
    return register_entity(
        db,
        entity_type="protocol_treasury",
        name=name,
        description=description or "Protocol-level treasury for fees and reserves.",
        owner_id=None,
        creator_id=governance_entity_id,
        status=EntityStatus.active,
        metadata=metadata,
        entity_id=entity_id,
    )


def validate_participants_for_submission(participants: list[dict[str, Any]], entities: dict[str, Entity]) -> None:
    """Advisory validation — warn via ValueError on unknown roles or type/role mismatch."""
    for p in participants:
        role = p.get("role")
        entity_id = p.get("entity_id")
        if not role or not entity_id:
            continue
        validate_participant_role(str(role))
        entity = entities.get(entity_id)
        if entity is None:
            continue
        from intelligence.entity_ontology import role_fits_entity_type

        if not role_fits_entity_type(str(role), entity.entity_type.value):
            raise ValueError(
                f"Role '{role}' is atypical for entity type '{entity.entity_type.value}' ({entity.name})"
            )
