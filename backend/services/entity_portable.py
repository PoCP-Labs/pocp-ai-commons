"""Resolve and create entities by portable cross-node identity."""

from sqlalchemy.orm import Session

from models.entity import Entity, EntityStatus, EntityType


def find_entity_by_portable_id(db: Session, portable_id: str) -> Entity | None:
    for entity in db.query(Entity).filter(Entity.metadata_.isnot(None)).all():
        metadata = entity.metadata_ or {}
        if metadata.get("portable_id") == portable_id:
            return entity
        provider = metadata.get("provider")
        provider_user_id = metadata.get("provider_user_id")
        if provider and provider_user_id and f"{provider}:{provider_user_id}" == portable_id:
            return entity
    return None


def resolve_or_create_portable_entity(db: Session, portable_id: str) -> Entity:
    entity = find_entity_by_portable_id(db, portable_id)
    if entity:
        return entity

    label = portable_id.split(":", 1)[-1] if ":" in portable_id else portable_id
    provider = portable_id.split(":", 1)[0] if ":" in portable_id else "external"
    external_ids = {provider: label} if provider not in ("dev", "github") else {}
    if provider == "github":
        external_ids["github"] = label

    entity = Entity(
        entity_type=EntityType.human,
        name=label,
        description=f"Federated identity resolved from {portable_id}",
        status=EntityStatus.active,
        metadata_={
            "portable_id": portable_id,
            "external_ids": external_ids,
            "federated": True,
        },
    )
    db.add(entity)
    db.flush()
    return entity
