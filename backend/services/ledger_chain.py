"""Append-only ledger with SHA-256 hash chain for tamper-evident audit."""

import hashlib
import json
from datetime import datetime

from sqlalchemy.orm import Session

from models.ledger import LedgerRecord


def _canonical_payload(payload: dict | None) -> str:
    return json.dumps(payload or {}, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def compute_record_hash(
    prev_hash: str | None,
    event_type: str,
    payload: dict | None,
    created_at: datetime,
) -> str:
    material = "|".join(
        [
            prev_hash or "",
            event_type,
            _canonical_payload(payload),
            created_at.isoformat(),
        ]
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _last_ledger_record(db: Session) -> LedgerRecord | None:
    return (
        db.query(LedgerRecord)
        .order_by(LedgerRecord.created_at.desc(), LedgerRecord.id.desc())
        .first()
    )


def append_ledger_record(
    db: Session,
    *,
    contribution_id: str | None,
    event_type: str,
    payload: dict | None,
) -> LedgerRecord:
    prev = _last_ledger_record(db)
    prev_hash = prev.record_hash if prev and prev.record_hash else None
    created_at = datetime.utcnow()
    record_hash = compute_record_hash(prev_hash, event_type, payload, created_at)
    record = LedgerRecord(
        contribution_id=contribution_id,
        event_type=event_type,
        payload=payload or {},
        prev_hash=prev_hash,
        record_hash=record_hash,
        created_at=created_at,
    )
    db.add(record)
    db.flush()
    return record


def backfill_ledger_hashes(db: Session) -> int:
    """Assign hash chain to legacy rows missing record_hash."""
    records = (
        db.query(LedgerRecord)
        .filter(LedgerRecord.record_hash.is_(None))
        .order_by(LedgerRecord.created_at.asc(), LedgerRecord.id.asc())
        .all()
    )
    if not records:
        return 0

    prev = (
        db.query(LedgerRecord)
        .filter(LedgerRecord.record_hash.isnot(None))
        .order_by(LedgerRecord.created_at.desc(), LedgerRecord.id.desc())
        .first()
    )
    prev_hash = prev.record_hash if prev else None

    for record in records:
        record.prev_hash = prev_hash
        record.record_hash = compute_record_hash(
            prev_hash, record.event_type, record.payload, record.created_at
        )
        prev_hash = record.record_hash

    db.flush()
    return len(records)


def verify_ledger_chain(db: Session) -> dict:
    records = (
        db.query(LedgerRecord)
        .order_by(LedgerRecord.created_at.asc(), LedgerRecord.id.asc())
        .all()
    )
    prev_hash: str | None = None
    for record in records:
        if not record.record_hash:
            return {"valid": False, "count": len(records), "first_broken_id": record.id}
        expected = compute_record_hash(
            prev_hash, record.event_type, record.payload, record.created_at
        )
        if record.record_hash != expected or record.prev_hash != prev_hash:
            return {"valid": False, "count": len(records), "first_broken_id": record.id}
        prev_hash = record.record_hash
    return {"valid": True, "count": len(records), "first_broken_id": None}
