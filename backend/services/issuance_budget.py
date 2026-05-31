"""Daily issuance budget — Bitcoin-style mint discipline for CP / AI Credits.

Issuance must flow through credit_transactions; this module caps aggregate daily mint.
"""

from __future__ import annotations

from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from models.wallet import CreditTransaction, CreditType
from services.protocol_config import get_rewards_config


def _day_start() -> datetime:
    now = datetime.utcnow()
    return datetime(now.year, now.month, now.day)


def _budget_config() -> dict:
    config = get_rewards_config().get("issuance_budget") or {}
    return {
        "enabled": bool(config.get("enabled", True)),
        "daily_cp_cap": float(config.get("daily_cp_cap", 5000)),
        "daily_bc_cap": float(config.get("daily_bc_cap", 20000)),
        "per_contribution_cp_cap": float(config.get("per_contribution_cp_cap", 200)),
        "per_contribution_bc_cap": float(config.get("per_contribution_bc_cap", 500)),
    }


def daily_issued_totals(db: Session) -> dict[str, float]:
    """Sum positive issuances since UTC midnight."""
    day = _day_start()
    rows = (
        db.query(CreditTransaction.credit_type, func.sum(CreditTransaction.amount))
        .filter(CreditTransaction.created_at >= day, CreditTransaction.amount > 0)
        .group_by(CreditTransaction.credit_type)
        .all()
    )
    totals = {"cp": 0.0, "ai_credits": 0.0}
    for credit_type, total in rows:
        key = credit_type.value if hasattr(credit_type, "value") else str(credit_type)
        if key == "cp":
            totals["cp"] = round(float(total or 0), 6)
        elif key == "ai_credits":
            totals["ai_credits"] = round(float(total or 0), 6)
    return totals


def issuance_budget_status(db: Session) -> dict:
    cfg = _budget_config()
    issued = daily_issued_totals(db)
    return {
        "enabled": cfg["enabled"],
        "day_start_utc": _day_start().isoformat(),
        "issued_today": issued,
        "caps": {
            "daily_cp": cfg["daily_cp_cap"],
            "daily_bc": cfg["daily_bc_cap"],
            "per_contribution_cp": cfg["per_contribution_cp_cap"],
            "per_contribution_bc": cfg["per_contribution_bc_cap"],
        },
        "remaining_today": {
            "cp": max(0.0, round(cfg["daily_cp_cap"] - issued["cp"], 6)),
            "ai_credits": max(0.0, round(cfg["daily_bc_cap"] - issued["ai_credits"], 6)),
        },
        "model": "bitcoin_inspired_issuance_discipline_v0.1",
    }


def assert_issuance_allowed(
    db: Session,
    *,
    cp_amount: float = 0.0,
    bc_amount: float = 0.0,
) -> None:
    """Raise HTTP 429 if this mint would exceed daily caps."""
    cfg = _budget_config()
    if not cfg["enabled"]:
        return

    cp_amount = max(0.0, float(cp_amount))
    bc_amount = max(0.0, float(bc_amount))

    if cp_amount > cfg["per_contribution_cp_cap"]:
        raise HTTPException(
            status_code=429,
            detail=f"Per-contribution CP cap exceeded: {cp_amount} > {cfg['per_contribution_cp_cap']}",
        )
    if bc_amount > cfg["per_contribution_bc_cap"]:
        raise HTTPException(
            status_code=429,
            detail=f"Per-contribution AI Credits cap exceeded: {bc_amount} > {cfg['per_contribution_bc_cap']}",
        )

    issued = daily_issued_totals(db)
    if issued["cp"] + cp_amount > cfg["daily_cp_cap"]:
        raise HTTPException(
            status_code=429,
            detail=f"Daily CP issuance cap reached ({cfg['daily_cp_cap']})",
        )
    if issued["ai_credits"] + bc_amount > cfg["daily_bc_cap"]:
        raise HTTPException(
            status_code=429,
            detail=f"Daily AI Credits issuance cap reached ({cfg['daily_bc_cap']})",
        )
