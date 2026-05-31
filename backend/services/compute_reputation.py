"""Compute provider reputation — Phase γ economics."""

from __future__ import annotations

import os
from typing import Any

from sqlalchemy.orm import Session

from models.reputation_audit import ReputationAuditEntry
from models.wallet import ReputationScore
from services.protocol_config import get_rewards_config
from services.reputation_audit import record_reputation_audit

COMPUTE_PROVIDER_CATEGORY = "compute_provider"
COMPUTE_REPUTATION_SOURCE = "compute_settlement"


def compute_provider_reputation_amount() -> float:
    cfg = get_rewards_config().get("compute_provider") or {}
    return float(
        cfg.get(
            "reputation_per_receipt",
            os.getenv("POCP_COMPUTE_PROVIDER_REPUTATION", "0.5"),
        )
    )


def get_compute_provider_reputation(db: Session, entity_id: str) -> float:
    row = (
        db.query(ReputationScore)
        .filter(
            ReputationScore.entity_id == entity_id,
            ReputationScore.category == COMPUTE_PROVIDER_CATEGORY,
        )
        .first()
    )
    return float(row.score) if row else 0.0


def load_compute_provider_reputation_map(db: Session) -> dict[str, float]:
    rows = (
        db.query(ReputationScore)
        .filter(ReputationScore.category == COMPUTE_PROVIDER_CATEGORY)
        .all()
    )
    return {row.entity_id: float(row.score) for row in rows}


def grant_compute_provider_reputation(
    db: Session,
    receipt: dict[str, Any],
    *,
    consumer_entity_id: str | None = None,
) -> dict[str, Any] | None:
    """Idempotent reputation grant per receipt hash."""
    provider_entity_id = receipt.get("provider_entity_id")
    receipt_hash = (receipt.get("integrity") or {}).get("receipt_hash")
    if not provider_entity_id or not receipt_hash:
        return None

    existing = (
        db.query(ReputationAuditEntry)
        .filter(
            ReputationAuditEntry.entity_id == provider_entity_id,
            ReputationAuditEntry.source == COMPUTE_REPUTATION_SOURCE,
            ReputationAuditEntry.reference_id == receipt_hash,
        )
        .first()
    )
    if existing:
        return {
            "granted": False,
            "reason": "already_granted",
            "provider_entity_id": provider_entity_id,
            "category": COMPUTE_PROVIDER_CATEGORY,
            "receipt_hash": receipt_hash,
            "balance": get_compute_provider_reputation(db, provider_entity_id),
        }

    amount = compute_provider_reputation_amount()
    rep = (
        db.query(ReputationScore)
        .filter(
            ReputationScore.entity_id == provider_entity_id,
            ReputationScore.category == COMPUTE_PROVIDER_CATEGORY,
        )
        .first()
    )
    if rep is None:
        rep = ReputationScore(
            entity_id=provider_entity_id,
            score=amount,
            category=COMPUTE_PROVIDER_CATEGORY,
        )
        db.add(rep)
    else:
        rep.score += amount
    db.flush()

    record_reputation_audit(
        db,
        entity_id=provider_entity_id,
        category=COMPUTE_PROVIDER_CATEGORY,
        delta=amount,
        balance_after=rep.score,
        source=COMPUTE_REPUTATION_SOURCE,
        reason=f"compute:{receipt.get('capability')}",
        reference_id=receipt_hash,
        actor_entity_id=consumer_entity_id or receipt.get("initiator_entity_id"),
        payload={
            "contribution_id": receipt.get("contribution_id"),
            "job_id": receipt.get("job_id"),
            "capability": receipt.get("capability"),
        },
    )
    return {
        "granted": True,
        "provider_entity_id": provider_entity_id,
        "category": COMPUTE_PROVIDER_CATEGORY,
        "delta": amount,
        "balance": rep.score,
        "receipt_hash": receipt_hash,
    }
