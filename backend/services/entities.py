"""Service layer for entity management business logic."""

from sqlalchemy.orm import Session

from models.entity import Entity, EntityStatus, EntityType
from models.wallet import Wallet
from services.contribution import grant_registration_credits


def create_entity(
    db: Session,
    entity_type: str,
    name: str,
    description: str | None = None,
    owner_id: str | None = None,
    creator_id: str | None = None,
) -> Entity:
    """Create a new entity with proper validation and side effects."""
    try:
        etype = EntityType(entity_type)
    except ValueError:
        raise ValueError(f"Invalid entity_type: {entity_type}. Must be one of: {[e.value for e in EntityType]}")

    # Validate owner exists
    if owner_id:
        owner = db.query(Entity).filter(Entity.id == owner_id).first()
        if not owner:
            raise ValueError(f"Owner entity not found: {owner_id}")

    entity = Entity(
        entity_type=etype,
        name=name,
        description=description,
        owner_id=owner_id,
        creator_id=creator_id or owner_id,
        status=EntityStatus.active,
    )
    db.add(entity)
    db.flush()

    # Auto-grant registration credits for humans
    wallet = grant_registration_credits(db, entity)

    return entity


def get_entity_by_id(db: Session, entity_id: str) -> Entity | None:
    """Get entity by ID with related data."""
    return (
        db.query(Entity)
        .filter(Entity.id == entity_id)
        .first()
    )


def list_entities(
    db: Session,
    entity_type: str | None = None,
    status: str | None = None,
    skip: int = 0,
    limit: int = 50,
) -> list[Entity]:
    """List entities with optional filters."""
    query = db.query(Entity)

    if entity_type:
        query = query.filter(Entity.entity_type == EntityType(entity_type))
    if status:
        query = query.filter(Entity.status == EntityStatus(status))

    return query.order_by(Entity.created_at).offset(skip).limit(limit).all()


def get_entity_wallet(db: Session, entity_id: str) -> Wallet | None:
    """Get wallet for an entity, creating one if it doesn't exist (for humans)."""
    wallet = db.query(Wallet).filter(Wallet.entity_id == entity_id).first()
    if wallet is None:
        entity = get_entity_by_id(db, entity_id)
        if entity and entity.entity_type == EntityType.human:
            wallet = grant_registration_credits(db, entity)
    return wallet
