from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from models.entity import Entity
from models.ledger import LedgerRecord
from models.wallet import ReputationScore, Wallet
from schemas import EntityOut, LedgerOut
from services.ledger_chain import verify_ledger_chain
from services.protocol_config import get_rewards_config

router = APIRouter(prefix="/api/v1", tags=["export"])


class LedgerVerifyOut(BaseModel):
    valid: bool
    count: int
    first_broken_id: str | None = None


class LedgerExportOut(BaseModel):
    spec_version: str
    exported_at: datetime
    records: list[LedgerOut]


class PortableEntityOut(BaseModel):
    spec_version: str
    entity: EntityOut
    portable_id: str | None = None
    external_ids: dict[str, str] = Field(default_factory=dict)
    wallet: dict | None = None
    reputation: list[dict] = Field(default_factory=list)


@router.get("/ledger/verify", response_model=LedgerVerifyOut)
def verify_ledger(db: Session = Depends(get_db)):
    return verify_ledger_chain(db)


@router.get("/ledger/export", response_model=LedgerExportOut)
def export_ledger(
    since: datetime | None = Query(default=None),
    db: Session = Depends(get_db),
):
    query = db.query(LedgerRecord).order_by(LedgerRecord.created_at.asc(), LedgerRecord.id.asc())
    if since is not None:
        query = query.filter(LedgerRecord.created_at >= since)
    records = query.all()
    return LedgerExportOut(
        spec_version=get_rewards_config().get("spec_version", "0.1"),
        exported_at=datetime.utcnow(),
        records=records,
    )


@router.get("/entities/{entity_id}/portable", response_model=PortableEntityOut)
def get_portable_entity(entity_id: str, db: Session = Depends(get_db)):
    entity = db.query(Entity).filter(Entity.id == entity_id).first()
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    metadata = entity.metadata_ or {}
    external_ids = dict(metadata.get("external_ids") or {})
    portable_id = metadata.get("portable_id")
    if not portable_id and metadata.get("provider") and metadata.get("provider_user_id"):
        portable_id = f"{metadata['provider']}:{metadata['provider_user_id']}"

    wallet = db.query(Wallet).filter(Wallet.entity_id == entity_id).first()
    reputation = db.query(ReputationScore).filter(ReputationScore.entity_id == entity_id).all()

    return PortableEntityOut(
        spec_version=get_rewards_config().get("spec_version", "0.1"),
        entity=entity,
        portable_id=portable_id,
        external_ids=external_ids,
        wallet={
            "cp_balance": wallet.cp_balance,
            "ai_credits": wallet.ai_credits,
        }
        if wallet
        else None,
        reputation=[
            {"category": r.category, "score": r.score, "updated_at": r.updated_at.isoformat()}
            for r in reputation
        ],
    )
