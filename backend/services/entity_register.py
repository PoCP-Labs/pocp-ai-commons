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
    meta.setdefault("ontology_version", "0.1")
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
