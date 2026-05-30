"""Invocation trace endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from database import get_db
from schemas import InvocationCreate, InvocationOut

router = APIRouter(prefix="/api/v1/invocations", tags=["invocations"])


@router.get("", response_model=list[InvocationOut])
def list_invocations(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    from models.invocation import InvocationTrace

    return (
        db.query(InvocationTrace)
        .options(joinedload(InvocationTrace.steps))
        .order_by(InvocationTrace.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.post("", response_model=InvocationOut, status_code=201)
def create_invocation(body: InvocationCreate, db: Session = Depends(get_db)):
    from models.invocation import InvocationTrace

    from services.invocation import record_invocation

    try:
        trace = record_invocation(
            db,
            initiator_id=body.initiator_id,
            skill_entity_id=body.skill_entity_id,
            agent_entity_id=body.agent_entity_id,
            model_provider=body.model_provider,
            task_id=body.task_id,
            contribution_id=body.contribution_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()
    return (
        db.query(InvocationTrace)
        .options(joinedload(InvocationTrace.steps))
        .filter(InvocationTrace.id == trace.id)
        .first()
    )
