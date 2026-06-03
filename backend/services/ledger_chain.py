"""Append-only ledger with hash chain for tamper-evident audit (crypto-agile)."""

import hashlib
import json
from datetime import datetime

from sqlalchemy.orm import Session

from models.ledger import LedgerRecord
from services.crypto_suite import active_hash_algorithm, hash_digest

LEGACY_HASH_ALGORITHM = "sha256"


def _canonical_payload(payload: dict | None) -> str:
    return json.dumps(payload or {}, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _created_at_iso(created_at: datetime | str) -> str:
    if isinstance(created_at, datetime):
        return created_at.isoformat()
    return str(created_at)


def compute_record_hash(
    prev_hash: str | None,
    event_type: str,
    payload: dict | None,
    created_at: datetime | str,
    hash_algorithm: str = LEGACY_HASH_ALGORITHM,
) -> str:
    material = "|".join(
        [
            prev_hash or "",
            event_type,
            _canonical_payload(payload),
            _created_at_iso(created_at),
        ]
    )
    if hash_algorithm == LEGACY_HASH_ALGORITHM:
        return hashlib.sha256(material.encode("utf-8")).hexdigest()
    return hash_digest(material, hash_algorithm)


def verify_ledger_records(records: list[dict]) -> dict:
    """Verify hash chain from exported or in-memory record dicts (no DB).

    Each record needs: event_type, payload, prev_hash, record_hash, created_at.
    Optional hash_algorithm (defaults to sha256 for legacy rows).
    """
    prev_hash: str | None = None
    genesis_hash: str | None = None
    tip_hash: str | None = None
    for index, record in enumerate(records):
        record_hash = record.get("record_hash")
        if not record_hash:
            return {
                "valid": False,
                "count": len(records),
                "verified_count": index,
                "first_broken_id": record.get("id"),
                "genesis_hash": genesis_hash,
                "tip_hash": tip_hash,
            }
        algorithm = record.get("hash_algorithm") or LEGACY_HASH_ALGORITHM
        expected = compute_record_hash(
            prev_hash,
            record["event_type"],
            record.get("payload"),
            record["created_at"],
            hash_algorithm=algorithm,
        )
        if record_hash != expected or record.get("prev_hash") != prev_hash:
            return {
                "valid": False,
                "count": len(records),
                "verified_count": index,
                "first_broken_id": record.get("id"),
                "genesis_hash": genesis_hash,
                "tip_hash": tip_hash,
            }
        if genesis_hash is None:
            genesis_hash = record_hash
        prev_hash = record_hash
        tip_hash = record_hash
    return {
        "valid": True,
        "count": len(records),
        "verified_count": len(records),
        "first_broken_id": None,
        "genesis_hash": genesis_hash,
        "tip_hash": tip_hash,
    }


def _last_ledger_record(db: Session) -> LedgerRecord | None:
    """Return the chain tip — the hashed row not referenced as anyone's prev_hash."""
    records = (
        db.query(LedgerRecord)
        .filter(LedgerRecord.record_hash.isnot(None))
        .all()
    )
    if not records:
        return None
    prev_targets = {r.prev_hash for r in records if r.prev_hash}
    tips = [r for r in records if r.record_hash not in prev_targets]
    if len(tips) == 1:
        return tips[0]
    return (
        db.query(LedgerRecord)
        .filter(LedgerRecord.record_hash.isnot(None))
        .order_by(LedgerRecord.created_at.desc(), LedgerRecord.id.desc())
        .first()
    )


def append_ledger_record(
    db: Session,
    *,
    contribution_id: str | None,
    event_type: str,
    payload: dict | None,
    hash_algorithm: str | None = None,
) -> LedgerRecord:
    prev = _last_ledger_record(db)
    prev_hash = prev.record_hash if prev and prev.record_hash else None
    created_at = datetime.utcnow()
    algorithm = hash_algorithm or active_hash_algorithm()
    record_hash = compute_record_hash(
        prev_hash, event_type, payload, created_at, hash_algorithm=algorithm
    )
    record = LedgerRecord(
        contribution_id=contribution_id,
        event_type=event_type,
        payload=payload or {},
        prev_hash=prev_hash,
        record_hash=record_hash,
        hash_algorithm=algorithm,
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
        algorithm = record.hash_algorithm or LEGACY_HASH_ALGORITHM
        record.prev_hash = prev_hash
        record.record_hash = compute_record_hash(
            prev_hash,
            record.event_type,
            record.payload,
            record.created_at,
            hash_algorithm=algorithm,
        )
        if not record.hash_algorithm:
            record.hash_algorithm = LEGACY_HASH_ALGORITHM
        prev_hash = record.record_hash

    db.flush()
    return len(records)


def _order_records_by_hash_chain(records: list[LedgerRecord]) -> list[LedgerRecord]:
    """Order ledger rows by prev_hash linkage (not created_at) for verify."""
    if not records:
        return []

    hashed = [r for r in records if r.record_hash]
    if not hashed:
        return sorted(records, key=lambda r: (r.created_at, r.id or ""))

    by_hash = {r.record_hash: r for r in hashed}
    prev_targets = {r.prev_hash for r in hashed if r.prev_hash}
    tips = [r for r in hashed if r.record_hash not in prev_targets]

    def _walk_from_tip(tip: LedgerRecord) -> list[LedgerRecord] | None:
        ordered_rev: list[LedgerRecord] = []
        current: LedgerRecord | None = tip
        seen: set[str] = set()
        while current and current.record_hash and current.record_hash not in seen:
            seen.add(current.record_hash)
            ordered_rev.append(current)
            current = by_hash.get(current.prev_hash) if current.prev_hash else None
        ordered = list(reversed(ordered_rev))
        return ordered if len(ordered) == len(hashed) else None

    if len(tips) == 1:
        ordered = _walk_from_tip(tips[0])
        if ordered is not None:
            return ordered

    genesis = [r for r in hashed if not r.prev_hash]
    if len(genesis) == 1:
        ordered: list[LedgerRecord] = []
        current: LedgerRecord | None = genesis[0]
        seen: set[str] = set()
        while current and current.record_hash not in seen:
            seen.add(current.record_hash)
            ordered.append(current)
            next_row = next(
                (by_hash[h] for h in by_hash if by_hash[h].prev_hash == current.record_hash),
                None,
            )
            current = next_row
        if len(ordered) == len(hashed):
            return ordered

    return sorted(hashed, key=lambda r: (r.created_at, r.id or ""))


def verify_ledger_chain(db: Session) -> dict:
    records = db.query(LedgerRecord).all()
    if not records:
        return {
            "valid": True,
            "count": 0,
            "verified_count": 0,
            "first_broken_id": None,
            "genesis_hash": None,
            "tip_hash": None,
        }
    ordered = _order_records_by_hash_chain(records)
    export_rows = [
        {
            "id": record.id,
            "event_type": record.event_type,
            "payload": record.payload,
            "prev_hash": record.prev_hash,
            "record_hash": record.record_hash,
            "hash_algorithm": record.hash_algorithm or LEGACY_HASH_ALGORITHM,
            "created_at": record.created_at,
        }
        for record in ordered
    ]
    return verify_ledger_records(export_rows)
