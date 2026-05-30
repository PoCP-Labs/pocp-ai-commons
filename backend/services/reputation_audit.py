"""Reputation change audit trail (Meritocrab-inspired)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from models.reputation_audit import ReputationAuditEntry


def record_reputation_audit(
    db: Session,
    *,
    entity_id: str,
    category: str,
    delta: float,
    balance_after: float,
    source: str,
    reason: str | None = None,
    reference_id: str | None = None,
    actor_entity_id: str | None = None,
    payload: dict[str, Any] | None = None,
) -> ReputationAuditEntry:
    entry = ReputationAuditEntry(
        entity_id=entity_id,
        category=category,
        delta=round(float(delta), 4),
        balance_after=round(float(balance_after), 4),
        source=source,
        reason=reason,
        reference_id=reference_id,
        actor_entity_id=actor_entity_id,
        payload=payload or {},
    )
    db.add(entry)
    db.flush()
    return entry


def list_reputation_audit(
    db: Session,
    entity_id: str,
    *,
    limit: int = 50,
) -> list[dict[str, Any]]:
    rows = (
        db.query(ReputationAuditEntry)
        .filter(ReputationAuditEntry.entity_id == entity_id)
        .order_by(ReputationAuditEntry.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": row.id,
            "entity_id": row.entity_id,
            "category": row.category,
            "delta": row.delta,
            "balance_after": row.balance_after,
            "source": row.source,
            "reason": row.reason,
            "reference_id": row.reference_id,
            "actor_entity_id": row.actor_entity_id,
            "payload": row.payload or {},
            "created_at": row.created_at.isoformat(),
        }
        for row in rows
    ]
