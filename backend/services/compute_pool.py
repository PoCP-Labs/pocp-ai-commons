"""Org ComputePool — reservoir for surplus credits and deficit burst (v0.3)."""

from __future__ import annotations

import os
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from models.entity import Entity, EntityType
from models.wallet import CreditTransaction, CreditType, Wallet
from services.ledger_chain import append_ledger_record
from services.protocol_config import get_rewards_config

COMPUTE_POOL_KEY = "compute_pool"


def _pool_cfg() -> dict[str, Any]:
    return get_rewards_config().get("compute_surplus") or {}


def pool_deposit_pct() -> float:
    return float(_pool_cfg().get("pool_deposit_pct") or 0.20)


def _default_pool() -> dict[str, Any]:
    return {
        "spec_version": "0.3",
        "balance_credits": 0.0,
        "total_deposited": 0.0,
        "total_spent": 0.0,
        "precompute_runs": 0,
        "policy": {
            "surplus_deposit_pct": pool_deposit_pct(),
            "deficit_burst_limit": float(_pool_cfg().get("deficit_burst_limit") or 500),
            "allow_external_adapter": False,
        },
    }


def _require_org(db: Session, org_entity_id: str) -> Entity:
    entity = db.get(Entity, org_entity_id)
    if not entity or entity.entity_type != EntityType.organization:
        raise HTTPException(status_code=404, detail="Organization entity not found")
    return entity


def get_compute_pool(db: Session, org_entity_id: str) -> dict[str, Any]:
    org = _require_org(db, org_entity_id)
    meta = dict(org.metadata_ or {})
    pool = meta.get(COMPUTE_POOL_KEY) or _default_pool()
    pool.setdefault("organization_entity_id", org_entity_id)
    return pool


def _save_pool(db: Session, org: Entity, pool: dict[str, Any]) -> dict[str, Any]:
    meta = dict(org.metadata_ or {})
    meta[COMPUTE_POOL_KEY] = pool
    org.metadata_ = meta
    flag_modified(org, "metadata_")
    db.flush()
    return pool


def get_pool_summary(db: Session, org_entity_id: str) -> dict[str, Any]:
    pool = get_compute_pool(db, org_entity_id)
    return {
        "organization_entity_id": org_entity_id,
        "balance_credits": pool.get("balance_credits", 0.0),
        "total_deposited": pool.get("total_deposited", 0.0),
        "total_spent": pool.get("total_spent", 0.0),
        "precompute_runs": pool.get("precompute_runs", 0),
        "deficit_burst_limit": (pool.get("policy") or {}).get("deficit_burst_limit"),
    }


def deposit_to_pool(
    db: Session,
    org_entity_id: str,
    amount: float,
    *,
    reason: str,
    source_entity_id: str | None = None,
    contribution_id: str | None = None,
) -> dict[str, Any]:
    if amount <= 0:
        raise HTTPException(status_code=400, detail="amount must be positive")
    org = _require_org(db, org_entity_id)
    pool = get_compute_pool(db, org_entity_id)
    pool["balance_credits"] = float(pool.get("balance_credits") or 0) + amount
    pool["total_deposited"] = float(pool.get("total_deposited") or 0) + amount
    _save_pool(db, org, pool)
    append_ledger_record(
        db,
        contribution_id=contribution_id,
        event_type="compute_pool_deposit",
        payload={
            "organization_entity_id": org_entity_id,
            "amount": amount,
            "reason": reason,
            "source_entity_id": source_entity_id,
            "balance_credits": pool["balance_credits"],
        },
    )
    return get_pool_summary(db, org_entity_id)


def spend_from_pool(
    db: Session,
    org_entity_id: str,
    amount: float,
    *,
    reason: str,
    beneficiary_entity_id: str | None = None,
    contribution_id: str | None = None,
) -> dict[str, Any]:
    if amount <= 0:
        raise HTTPException(status_code=400, detail="amount must be positive")
    org = _require_org(db, org_entity_id)
    pool = get_compute_pool(db, org_entity_id)
    balance = float(pool.get("balance_credits") or 0)
    if balance < amount:
        raise HTTPException(status_code=402, detail="Insufficient compute pool balance")

    pool["balance_credits"] = balance - amount
    pool["total_spent"] = float(pool.get("total_spent") or 0) + amount
    _save_pool(db, org, pool)

    if beneficiary_entity_id:
        wallet = db.query(Wallet).filter(Wallet.entity_id == beneficiary_entity_id).first()
        if wallet:
            wallet.ai_credits += amount
            db.add(
                CreditTransaction(
                    wallet_id=wallet.id,
                    amount=amount,
                    credit_type=CreditType.ai_credits,
                    reason=f"compute_pool:{reason[:40]}",
                    contribution_id=contribution_id,
                )
            )

    append_ledger_record(
        db,
        contribution_id=contribution_id,
        event_type="compute_pool_spend",
        payload={
            "organization_entity_id": org_entity_id,
            "amount": amount,
            "reason": reason,
            "beneficiary_entity_id": beneficiary_entity_id,
            "balance_credits": pool["balance_credits"],
        },
    )
    return get_pool_summary(db, org_entity_id)


def maybe_deposit_surplus_from_settlement(
    db: Session,
    *,
    org_entity_id: str | None,
    provider_entity_id: str,
    credits_granted: float,
    receipt_hash: str | None,
) -> dict[str, Any] | None:
    """After provider settlement, optionally deposit a % into org pool."""
    if not org_entity_id or credits_granted <= 0:
        return None
    if os.getenv("POCP_COMPUTE_POOL_AUTO_DEPOSIT", "true").lower() not in ("1", "true", "yes"):
        return None
    pct = pool_deposit_pct()
    amount = round(credits_granted * pct, 4)
    if amount <= 0:
        return None
    wallet = db.query(Wallet).filter(Wallet.entity_id == provider_entity_id).first()
    if wallet and wallet.ai_credits >= amount:
        wallet.ai_credits -= amount
        db.add(
            CreditTransaction(
                wallet_id=wallet.id,
                amount=-amount,
                credit_type=CreditType.ai_credits,
                reason=f"pool_surplus:{(receipt_hash or '')[:12]}",
            )
        )
    return deposit_to_pool(
        db,
        org_entity_id,
        amount,
        reason="surplus_auto_deposit_from_provider_settlement",
        source_entity_id=provider_entity_id,
    )
