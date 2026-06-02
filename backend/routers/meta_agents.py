"""Meta Agent roster API — engineering orchestration entities."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from schemas.meta_agent import MetaAgentOut, MetaAgentRosterOut
from services.meta_agent_registry import (
    ensure_meta_agents,
    get_meta_agent,
    list_meta_agents,
    meta_agent_roster_summary,
)

router = APIRouter(prefix="/api/v1/meta-agents", tags=["meta-agents"])


@router.get("/roster", response_model=MetaAgentRosterOut)
def get_meta_agent_roster():
    return meta_agent_roster_summary()


@router.get("", response_model=list[MetaAgentOut])
def list_meta_agents_endpoint(db: Session = Depends(get_db)):
    return list_meta_agents(db)


@router.get("/{entity_id}", response_model=MetaAgentOut)
def get_meta_agent_endpoint(entity_id: str, db: Session = Depends(get_db)):
    row = get_meta_agent(db, entity_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Meta Agent not found")
    return row


@router.post("/ensure", response_model=list[str])
def ensure_meta_agents_endpoint(db: Session = Depends(get_db)):
    """Idempotently register all Meta Agents (also runs on app startup)."""
    ids = ensure_meta_agents(db)
    db.commit()
    return ids
