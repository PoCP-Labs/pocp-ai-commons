"""Exchange spine read API — exchange detail, proof, entity local chain."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from models.user_account import UserAccount
from routers.auth import require_current_user
from schemas import ContributionOut
from services.entity_local_chain import build_entity_local_chain, find_exchange_ledger_record
from services.exchange_contribution import publish_contribution_from_exchange
from services.exchange_proof import build_exchange_proof_packet
from services.invocation_ledger import verify_exchange_invocation_chain

router = APIRouter(prefix="/api/v1", tags=["exchanges"])


class ExchangePublishContributionIn(BaseModel):
    task_id: str
    description: str | None = None
    contribution_type: str = "knowledge"
    extra_evidence: dict[str, Any] = Field(default_factory=dict)


@router.get("/entities/{entity_id}/local-chain")
def get_entity_local_chain(
    entity_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    cursor: int | None = Query(default=None, ge=1),
    db: Session = Depends(get_db),
):
    """Read-only Entity Local Chain (ELC) — participation view over exchange_settled rows."""
    from models.entity import Entity

    if db.get(Entity, entity_id) is None:
        raise HTTPException(status_code=404, detail="Entity not found")
    return build_entity_local_chain(db, entity_id, limit=limit, cursor=cursor)


@router.get("/exchanges/{exchange_id}")
def get_exchange(exchange_id: str, db: Session = Depends(get_db)):
    record = find_exchange_ledger_record(db, exchange_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Exchange not found")
    payload = record.payload or {}
    return {
        "exchange_id": exchange_id,
        "ledger_record_id": record.id,
        "ledger_record_hash": record.record_hash,
        "created_at": record.created_at.isoformat() if record.created_at else None,
        **payload,
    }


@router.get("/exchanges/{exchange_id}/proof")
def get_exchange_proof(exchange_id: str, db: Session = Depends(get_db)):
    packet = build_exchange_proof_packet(db, exchange_id)
    if packet is None:
        raise HTTPException(status_code=404, detail="Exchange not found")
    return packet


@router.get("/exchanges/{exchange_id}/integrity")
def get_exchange_integrity(exchange_id: str, db: Session = Depends(get_db)):
    """Verify invocation_ref ↔ receipt ↔ settlement linkage for an exchange."""
    result = verify_exchange_invocation_chain(db, exchange_id)
    if result.get("reason") == "exchange_not_found":
        raise HTTPException(status_code=404, detail="Exchange not found")
    return result


@router.post(
    "/exchanges/{exchange_id}/publish-contribution",
    response_model=ContributionOut,
    status_code=201,
)
def publish_exchange_as_contribution(
    exchange_id: str,
    body: ExchangePublishContributionIn,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(require_current_user),
):
    """Opt-in upgrade: attach settled exchange as contribution evidence (Contribution Chain)."""
    contribution = publish_contribution_from_exchange(
        db,
        exchange_id=exchange_id,
        human_entity_id=current_user.entity_id,
        task_id=body.task_id,
        description=body.description,
        contribution_type=body.contribution_type,
        extra_evidence=body.extra_evidence,
    )
    db.commit()
    db.refresh(contribution)
    return contribution
