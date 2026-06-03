"""Public reference capability registry — register and search without commercial ranking."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from models.capability import (
    CapabilityAvailability,
    CapabilityType,
    CapabilityUnit,
    EntityCapability,
    PriceModel,
)
from models.entity import Entity
from services.capability.base import CapabilityDescriptor


SUPPORTED_UNITS = {"CP", "AIC", "CC", "PT"}


def _parse_enum(enum_cls: type, value: str):
    try:
        return enum_cls(value)
    except ValueError as exc:
        raise ValueError(f"Invalid {enum_cls.__name__}: {value}") from exc


def descriptor_from_record(record: EntityCapability) -> CapabilityDescriptor:
    accepted = record.accepted_units if isinstance(record.accepted_units, list) else ["AIC"]
    return CapabilityDescriptor(
        capability_id=record.id,
        entity_id=record.entity_id,
        capability_type=record.capability_type.value,
        name=record.name,
        unit=record.unit.value,
        price_model=record.price_model.value,
        base_price=record.base_price,
        accepted_units=accepted,
        verification_method=record.verification_method,
        availability=record.availability.value,
        reputation_score=record.reputation_score,
        risk_level=record.risk_level,
        metadata=dict(record.metadata_ or {}),
    )


def register_capability(
    db: Session,
    *,
    entity_id: str,
    capability_type: str,
    name: str,
    unit: str,
    price_model: str = "fixed",
    base_price: float = 0.0,
    accepted_units: list[str] | None = None,
    verification_method: str = "human_review",
    availability: str = "available",
    reputation_score: float = 0.0,
    risk_level: str = "low",
    metadata: dict[str, Any] | None = None,
    capability_id: str | None = None,
) -> EntityCapability:
    entity = db.get(Entity, entity_id)
    if not entity:
        raise ValueError(f"Entity not found: {entity_id}")

    units = accepted_units or ["AIC"]
    invalid = set(units) - SUPPORTED_UNITS
    if invalid:
        raise ValueError(f"Unsupported accepted_units: {sorted(invalid)}")

    record = EntityCapability(
        entity_id=entity_id,
        capability_type=_parse_enum(CapabilityType, capability_type),
        name=name.strip(),
        unit=_parse_enum(CapabilityUnit, unit),
        price_model=_parse_enum(PriceModel, price_model),
        base_price=base_price,
        accepted_units=units,
        verification_method=verification_method,
        availability=_parse_enum(CapabilityAvailability, availability),
        reputation_score=reputation_score,
        risk_level=risk_level,
        metadata_=dict(metadata or {}),
    )
    if capability_id:
        record.id = capability_id
    db.add(record)
    db.flush()
    return record


def get_capability(db: Session, capability_id: str) -> EntityCapability | None:
    return db.get(EntityCapability, capability_id)


def search_capabilities(
    db: Session,
    *,
    capability_type: str | None = None,
    entity_id: str | None = None,
    availability: str | None = None,
    name: str | None = None,
    limit: int = 100,
) -> list[EntityCapability]:
    query = db.query(EntityCapability)
    if capability_type:
        query = query.filter(
            EntityCapability.capability_type == _parse_enum(CapabilityType, capability_type)
        )
    if entity_id:
        query = query.filter(EntityCapability.entity_id == entity_id)
    if availability:
        query = query.filter(
            EntityCapability.availability == _parse_enum(CapabilityAvailability, availability)
        )
    if name:
        query = query.filter(EntityCapability.name.ilike(f"%{name.strip()}%"))
    return query.order_by(EntityCapability.created_at.desc()).limit(limit).all()
