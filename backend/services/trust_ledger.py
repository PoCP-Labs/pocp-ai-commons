"""Record trust-list changes in the append-only ledger."""

from sqlalchemy.orm import Session

from models.ledger import LedgerRecord
from services.ledger_chain import append_ledger_record
from services.trust_config import canonical_trust_payload, load_trusted_nodes, trust_list_hash, trusted_nodes_source


def _last_trust_hash(db: Session) -> str | None:
    record = (
        db.query(LedgerRecord)
        .filter(LedgerRecord.event_type == "trust_list_updated")
        .order_by(LedgerRecord.created_at.desc(), LedgerRecord.id.desc())
        .first()
    )
    if record is None:
        return None
    payload = record.payload or {}
    return payload.get("trust_list_hash")


def record_trust_list_if_changed(db: Session) -> dict | None:
    nodes = load_trusted_nodes()
    current_hash = trust_list_hash(nodes)
    previous_hash = _last_trust_hash(db)
    if previous_hash == current_hash:
        return None

    payload = {
        "trust_list_hash": current_hash,
        "source": trusted_nodes_source(),
        "node_count": len(nodes),
        "trusted_nodes": canonical_trust_payload(nodes),
        "previous_hash": previous_hash,
    }
    append_ledger_record(
        db,
        contribution_id=None,
        event_type="trust_list_updated",
        payload=payload,
    )
    db.flush()
    return payload
