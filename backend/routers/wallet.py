from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models.wallet import CreditType
from routers.auth import current_user_from_header
from schemas import CreditTransactionOut, WalletQuoteOut, WalletSummaryOut, WalletTransactionsOut
from services.wallet_service import (
    export_wallet_bundle,
    list_wallet_transactions,
    quote_spend,
    verify_entity_wallet_export,
    wallet_summary,
)

router = APIRouter(prefix="/api/v1/wallets", tags=["wallets"])


class WalletQuoteIn(BaseModel):
    action: str = "ai_chat"
    provider: str | None = None


def _require_user(authorization: str | None, db: Session):
    return current_user_from_header(authorization, db)


@router.get("/me/summary", response_model=WalletSummaryOut)
def me_wallet_summary(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    user = _require_user(authorization, db)
    return wallet_summary(db, user.entity_id)


@router.get("/me/transactions", response_model=WalletTransactionsOut)
def me_wallet_transactions(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    credit_type: str | None = Query(default=None, description="cp or ai_credits"),
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    user = _require_user(authorization, db)
    ct: CreditType | None = None
    if credit_type:
        try:
            ct = CreditType(credit_type)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="credit_type must be cp or ai_credits") from exc
    return list_wallet_transactions(db, user.entity_id, limit=limit, offset=offset, credit_type=ct)


@router.get("/me/export")
def me_wallet_export(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    """Downloadable wallet + transaction bundle for the authenticated Entity."""
    user = _require_user(authorization, db)
    return export_wallet_bundle(db, user.entity_id)


@router.post("/me/export/verify")
def me_wallet_export_verify(export: dict):
    """Offline-style verify of a GET /wallets/me/export JSON bundle."""
    return verify_entity_wallet_export(export)


@router.post("/me/quote", response_model=WalletQuoteOut)
def me_wallet_quote(
    body: WalletQuoteIn,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    user = _require_user(authorization, db)
    try:
        return quote_spend(db, user.entity_id, body.action, provider=body.provider)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{entity_id}/summary", response_model=WalletSummaryOut)
def entity_wallet_summary(entity_id: str, db: Session = Depends(get_db)):
    """Public read — wallet summary for any Entity (dashboard / entity profile)."""
    from models.entity import Entity

    if not db.query(Entity).filter(Entity.id == entity_id).first():
        raise HTTPException(status_code=404, detail="Entity not found")
    return wallet_summary(db, entity_id)


@router.get("/{entity_id}/transactions", response_model=WalletTransactionsOut)
def entity_wallet_transactions(
    entity_id: str,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    credit_type: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    from models.entity import Entity

    if not db.query(Entity).filter(Entity.id == entity_id).first():
        raise HTTPException(status_code=404, detail="Entity not found")
    ct: CreditType | None = None
    if credit_type:
        try:
            ct = CreditType(credit_type)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="credit_type must be cp or ai_credits") from exc
    return list_wallet_transactions(db, entity_id, limit=limit, offset=offset, credit_type=ct)
