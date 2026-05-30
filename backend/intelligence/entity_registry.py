"""Register contribution-capable entities through the capability layer."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from intelligence.protocol import ENTITY_TYPES, entity_can_contribute
from models.entity import Entity, EntityStatus, EntityType
from services.contribution import grant_registration_credits


def register_contribution_entity(
    db: Session,
    *,
    entity_type: str,
    name: str,
    description: str | None,
    tags: list[str],
    capabilities: list[str],
    owner_id: str | None,
    creator_id: str | None,
) -> Entity:
    if entity_type not in ENTITY_TYPES:
        raise ValueError(f"Unsupported entity_type: {entity_type}")
    if not entity_can_contribute(entity_type):
        raise ValueError(f"Entity type cannot contribute: {entity_type}")

    try:
        et = EntityType(entity_type)
    except ValueError as exc:
        raise ValueError(f"Invalid entity_type: {entity_type}") from exc

    metadata: dict[str, Any] = {
        "contribution_capable": True,
        "registered_via": "capability_layer",
        "tags": tags,
        "capabilities": capabilities,
        "principle": "Everything connects through verified contribution.",
    }

    entity = Entity(
        entity_type=et,
        name=name,
        description=description,
        owner_id=owner_id,
        creator_id=creator_id,
        status=EntityStatus.active,
        metadata_=metadata,
    )
    db.add(entity)
    db.flush()
    grant_registration_credits(db, entity)
    db.flush()
    return entity
