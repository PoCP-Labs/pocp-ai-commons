"""Wallet and ledger endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models.ledger import LedgerRecord
from models.wallet import ReputationScore, Wallet
from schemas import LedgerOut, ReputationOut, WalletOut

router = APIRouter(prefix="/api/v1", tags=["wallets", "ledger"])


@router.get("/wallets", response_model=list[WalletOut])
def list_wallets(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    return db.query(Wallet).offset(skip).limit(limit).all()


@router.get("/wallets/{entity_id}", response_model=WalletOut)
def get_wallet(entity_id: str, db: Session = Depends(get_db)):
    wallet = db.query(Wallet).filter(Wallet.entity_id == entity_id).first()
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found for entity")
    return wallet


@router.get("/reputation", response_model=list[ReputationOut])
def list_reputation(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    return db.query(ReputationScore).order_by(ReputationScore.score.desc()).offset(skip).limit(limit).all()


@router.get("/ledger", response_model=list[LedgerOut])
def list_ledger(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(LedgerRecord).order_by(LedgerRecord.created_at.desc()).offset(skip).limit(limit).all()
