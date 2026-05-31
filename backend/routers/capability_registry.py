"""Neural Commons v0.4 — capability registry API (register + search)."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from models.entity import Entity
from models.user_account import UserAccount
from routers.auth import require_current_user
from services.capability.registry import (
    descriptor_from_record,
    get_capability,
    register_capability,
    search_capabilities,
)
from services.entity_management import assert_entity_governable_by_actor

router = APIRouter(prefix="/api/v1/registry/capabilities", tags=["capability-registry"])


class CapabilityRegisterIn(BaseModel):
    entity_id: str
    capability_type: str
    name: str = Field(min_length=1, max_length=255)
    unit: str
    price_model: str = "fixed"
    base_price: float = 0.0
    accepted_units: list[str] = Field(default_factory=lambda: ["AIC"])
    verification_method: str = "human_review"
    availability: str = "available"
    reputation_score: float = 0.0
    risk_level: str = "low"
    metadata: dict[str, Any] = Field(default_factory=dict)


class CapabilityOut(BaseModel):
    capability_id: str
    entity_id: str
    capability_type: str
    name: str
    unit: str
    price_model: str
    base_price: float
    accepted_units: list[str]
    verification_method: str
    availability: str
    reputation_score: float
    risk_level: str
    metadata: dict[str, Any] = Field(default_factory=dict)


def _to_out(record) -> CapabilityOut:
    desc = descriptor_from_record(record)
    return CapabilityOut(
        capability_id=desc.capability_id,
        entity_id=desc.entity_id,
        capability_type=desc.capability_type,
        name=desc.name,
        unit=desc.unit,
        price_model=desc.price_model,
        base_price=desc.base_price,
        accepted_units=desc.accepted_units,
        verification_method=desc.verification_method,
        availability=desc.availability,
        reputation_score=desc.reputation_score,
        risk_level=desc.risk_level,
        metadata=desc.metadata,
    )


@router.get("", response_model=dict)
def list_capabilities(
    capability_type: str | None = Query(default=None),
    entity_id: str | None = Query(default=None),
    availability: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    try:
        rows = search_capabilities(
            db,
            capability_type=capability_type,
            entity_id=entity_id,
            availability=availability,
            limit=limit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    items = [_to_out(row) for row in rows]
    return {"count": len(items), "items": items, "spec_version": "0.3"}


@router.post("", response_model=CapabilityOut, status_code=201)
def create_capability(
    body: CapabilityRegisterIn,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(require_current_user),
):
    try:
        entity = db.get(Entity, body.entity_id)
        if not entity:
            raise HTTPException(status_code=404, detail="Entity not found")
        assert_entity_governable_by_actor(db, entity, current_user.entity_id)
        record = register_capability(
            db,
            entity_id=body.entity_id,
            capability_type=body.capability_type,
            name=body.name,
            unit=body.unit,
            price_model=body.price_model,
            base_price=body.base_price,
            accepted_units=body.accepted_units,
            verification_method=body.verification_method,
            availability=body.availability,
            reputation_score=body.reputation_score,
            risk_level=body.risk_level,
            metadata=body.metadata,
        )
        db.commit()
        db.refresh(record)
    except HTTPException:
        raise
    except ValueError as exc:
        detail = str(exc)
        status = 403 if "Not authorized" in detail or "Genesis" in detail else 400
        raise HTTPException(status_code=status, detail=detail) from exc
    return _to_out(record)


@router.get("/{capability_id}", response_model=CapabilityOut)
def read_capability(capability_id: str, db: Session = Depends(get_db)):
    record = get_capability(db, capability_id)
    if not record:
        raise HTTPException(status_code=404, detail="Capability not found")
    return _to_out(record)
