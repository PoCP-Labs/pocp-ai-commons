"""Platform Entity lifecycle helpers — list filters and owner-scoped updates."""

from __future__ import annotations

from sqlalchemy.orm import Session

from genesis import GENESIS_ENTITY_IDS
from intelligence.entity_ontology import validate_entity_type
from models.entity import Entity, EntityStatus, EntityType
from services.org_foundation import can_sponsor_as_organization


def query_entities(
    db: Session,
    *,
    entity_type: str | None = None,
    status: str | None = None,
    owner_id: str | None = None,
    q: str | None = None,
    genesis_only: bool = False,
) -> list[Entity]:
    query = db.query(Entity)
    if genesis_only:
        query = query.filter(Entity.id.in_(GENESIS_ENTITY_IDS))
    if entity_type:
        validate_entity_type(entity_type)
        query = query.filter(Entity.entity_type == EntityType(entity_type))
    if status:
        query = query.filter(Entity.status == EntityStatus(status))
    if owner_id:
        query = query.filter(Entity.owner_id == owner_id)
    if q:
        like = f"%{q.strip()}%"
        query = query.filter(Entity.name.ilike(like) | Entity.description.ilike(like))
    return query.order_by(Entity.created_at).all()


def actor_can_govern_entity(db: Session, entity: Entity, actor_entity_id: str) -> bool:
    if entity.id in GENESIS_ENTITY_IDS:
        return False
    if actor_entity_id in (entity.owner_id, entity.creator_id):
        return True
    if entity.owner_id:
        owner = db.get(Entity, entity.owner_id)
        if owner and owner.entity_type == EntityType.organization:
            return can_sponsor_as_organization(db, owner.id, actor_entity_id)
    return False


def assert_entity_governable_by_actor(db: Session, entity: Entity, actor_entity_id: str) -> None:
    if entity.id in GENESIS_ENTITY_IDS:
        raise ValueError("Genesis entities are managed by protocol bootstrap only")
    if not actor_can_govern_entity(db, entity, actor_entity_id):
        raise ValueError("Not authorized to govern this entity")


def assert_entity_mutable_by_actor(db: Session, entity: Entity, actor_entity_id: str) -> None:
    assert_entity_governable_by_actor(db, entity, actor_entity_id)


def list_pending_for_actor(db: Session, actor_entity_id: str) -> list[Entity]:
    pending = (
        db.query(Entity)
        .filter(Entity.status == EntityStatus.pending)
        .order_by(Entity.created_at)
        .all()
    )
    return [e for e in pending if actor_can_govern_entity(db, e, actor_entity_id)]


def review_entity(
    db: Session,
    entity: Entity,
    *,
    actor_entity_id: str,
    action: str,
    feedback: str | None = None,
) -> Entity:
    assert_entity_governable_by_actor(db, entity, actor_entity_id)
    if entity.status != EntityStatus.pending:
        raise ValueError(f"Entity is not pending review (status={entity.status.value})")

    action = action.lower().strip()
    if action == "approve":
        entity.status = EntityStatus.active
    elif action == "reject":
        entity.status = EntityStatus.inactive
    else:
        raise ValueError("action must be 'approve' or 'reject'")

    meta = dict(entity.metadata_ or {})
    meta["review"] = {
        "action": action,
        "reviewer_entity_id": actor_entity_id,
        "feedback": feedback,
    }
    entity.metadata_ = meta
    return entity


def apply_entity_patch(entity: Entity, *, name: str | None, description: str | None, status: str | None, metadata: dict | None) -> Entity:
    if name is not None:
        entity.name = name.strip()
    if description is not None:
        entity.description = description
    if status is not None:
        entity.status = EntityStatus(status)
    if metadata is not None:
        merged = dict(entity.metadata_ or {})
        merged.update(metadata)
        entity.metadata_ = merged
    return entity
