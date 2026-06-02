"""Capability-bound invocation API — PR-07."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from services.capability_invocation.store import (
    complete_capability_invocation,
    create_capability_invocation,
    get_capability_invocation,
    invocation_ref_from_record,
    list_capability_invocations,
    record_to_dict,
    transition_capability_invocation,
)

router = APIRouter(prefix="/api/v1/invocations/capability", tags=["capability-invocations"])


class CapabilityInvocationCreate(BaseModel):
    caller_entity_id: str
    callee_entity_id: str
    capability_id: str
    input_payload: dict[str, Any] | None = None
    input_hash: str | None = None
    task_id: str | None = None
    trace_id: str | None = None
    cost_unit: str | None = None
    cost_amount: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class CapabilityInvocationComplete(BaseModel):
    output_payload: dict[str, Any] | None = None
    output_hash: str | None = None


class CapabilityInvocationTransition(BaseModel):
    status: str


@router.post("", status_code=201)
def create_capability_invocation_endpoint(
    body: CapabilityInvocationCreate,
    db: Session = Depends(get_db),
):
    try:
        record = create_capability_invocation(
            db,
            caller_entity_id=body.caller_entity_id,
            callee_entity_id=body.callee_entity_id,
            capability_id=body.capability_id,
            input_payload=body.input_payload,
            input_hash=body.input_hash,
            task_id=body.task_id,
            trace_id=body.trace_id,
            cost_unit=body.cost_unit,
            cost_amount=body.cost_amount,
            metadata=body.metadata,
        )
        db.commit()
        return record_to_dict(record)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("")
def list_capability_invocations_endpoint(
    caller_entity_id: str | None = Query(None),
    callee_entity_id: str | None = Query(None),
    capability_id: str | None = Query(None),
    status: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    rows = list_capability_invocations(
        db,
        caller_entity_id=caller_entity_id,
        callee_entity_id=callee_entity_id,
        capability_id=capability_id,
        status=status,
        limit=limit,
    )
    return [record_to_dict(row) for row in rows]


@router.get("/{invocation_id}")
def get_capability_invocation_endpoint(invocation_id: str, db: Session = Depends(get_db)):
    record = get_capability_invocation(db, invocation_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Invocation not found")
    payload = record_to_dict(record)
    payload["invocation_ref"] = invocation_ref_from_record(record)
    return payload


@router.post("/{invocation_id}/complete")
def complete_capability_invocation_endpoint(
    invocation_id: str,
    body: CapabilityInvocationComplete,
    db: Session = Depends(get_db),
):
    try:
        record = complete_capability_invocation(
            db,
            invocation_id,
            output_payload=body.output_payload,
            output_hash=body.output_hash,
        )
        db.commit()
        return record_to_dict(record)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{invocation_id}/transition")
def transition_capability_invocation_endpoint(
    invocation_id: str,
    body: CapabilityInvocationTransition,
    db: Session = Depends(get_db),
):
    try:
        record = transition_capability_invocation(db, invocation_id, status=body.status)
        db.commit()
        return record_to_dict(record)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
