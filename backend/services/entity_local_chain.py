"""Entity Local Chain (ELC) — read-only participation view over exchange_settled rows."""

from __future__ import annotations

import hashlib
from typing import Any

from sqlalchemy.orm import Session

from models.ledger import LedgerRecord
from services.ledger_chain import _order_records_by_hash_chain
from services.ledger_merkle import build_inclusion_bundle

ELC_VERSION = "0.1"
ELC_SPEC = "pocp.entity_local_chain.v0.1"


def _entity_participates(payload: dict[str, Any], entity_id: str) -> bool:
    if payload.get("consumer_entity_id") == entity_id:
        return True
    providers = payload.get("provider_entity_ids") or []
    return entity_id in providers


def _all_ledger_hashes(db: Session) -> list[str]:
    records = (
        db.query(LedgerRecord)
        .filter(LedgerRecord.record_hash.isnot(None))
        .all()
    )
    ordered = _order_records_by_hash_chain(records)
    return [r.record_hash for r in ordered if r.record_hash]


def _elc_record_hash(prev_hash: str | None, kind: str, ref_id: str, grc_id: str) -> str:
    material = "|".join([prev_hash or "", kind, ref_id or "", grc_id])
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def build_entity_local_chain(
    db: Session,
    entity_id: str,
    *,
    limit: int = 50,
    cursor: int | None = None,
) -> dict[str, Any]:
    """Build ELC view from GRC exchange_settled rows (not a second source of truth)."""
    rows = (
        db.query(LedgerRecord)
        .filter(LedgerRecord.event_type == "exchange_settled")
        .order_by(LedgerRecord.created_at.asc(), LedgerRecord.id.asc())
        .all()
    )
    matched = [r for r in rows if _entity_participates(r.payload or {}, entity_id)]

    elc_records: list[dict[str, Any]] = []
    prev_hash: str | None = None
    ledger_hashes = _all_ledger_hashes(db)

    for seq, record in enumerate(matched, start=1):
        payload = record.payload or {}
        ref_id = str(payload.get("exchange_id") or record.id)
        kind = "exchange_settled"
        record_hash = _elc_record_hash(prev_hash, kind, ref_id, record.id)
        spv = None
        if record.record_hash and ledger_hashes:
            spv = build_inclusion_bundle(ledger_hashes, record.record_hash)

        elc_records.append(
            {
                "seq": seq,
                "kind": kind,
                "ref_id": ref_id,
                "exchange_kind": payload.get("exchange_kind"),
                "grc_ledger_record_id": record.id,
                "grc_record_hash": record.record_hash,
                "receipt_hash": payload.get("receipt_hash"),
                "usage": payload.get("usage"),
                "spv": spv,
                "prev_hash": prev_hash,
                "record_hash": record_hash,
                "created_at": record.created_at.isoformat() if record.created_at else None,
            }
        )
        prev_hash = record_hash

    total = len(elc_records)
    start = max(0, (cursor or 1) - 1)
    if cursor is None and total > limit:
        page = elc_records[-limit:]
        next_cursor = max(1, total - limit + 1) if total > limit else None
    else:
        page = elc_records[start : start + limit]
        next_cursor = start + limit + 1 if start + limit < total else None

    head_hash = elc_records[-1]["record_hash"] if elc_records else None

    return {
        "elc_version": ELC_VERSION,
        "elc_spec": ELC_SPEC,
        "entity_id": entity_id,
        "head_hash": head_hash,
        "total": total,
        "limit": limit,
        "cursor": cursor,
        "next_cursor": next_cursor,
        "records": page,
        "note": "ELC is a participation view; GRC ledger remains canonical truth.",
    }


def find_elc_record_for_exchange(
    db: Session,
    entity_id: str,
    exchange_id: str,
    *,
    limit: int = 500,
) -> dict[str, Any] | None:
    """Return the ELC participation row whose ref_id matches exchange_id, if any."""
    view = build_entity_local_chain(db, entity_id, limit=limit)
    for record in view.get("records") or []:
        if record.get("ref_id") == exchange_id:
            return record
    return None


def find_exchange_ledger_record(db: Session, exchange_id: str) -> LedgerRecord | None:
    for record in (
        db.query(LedgerRecord)
        .filter(LedgerRecord.event_type == "exchange_settled")
        .order_by(LedgerRecord.created_at.desc())
        .all()
    ):
        payload = record.payload or {}
        if payload.get("exchange_id") == exchange_id:
            return record
    return None
