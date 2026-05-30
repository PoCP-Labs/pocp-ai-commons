"""Ledger Merkle root anchor for external verification."""

import hashlib
import os
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from models.ledger import LedgerRecord
from services.federation_crypto import get_node_public_key_hex, sign_message
from services.ledger_chain import verify_ledger_chain
from services.protocol_config import get_rewards_config


def merkle_root(hashes: list[str]) -> str:
    if not hashes:
        return hashlib.sha256(b"").hexdigest()
    layer = hashes[:]
    while len(layer) > 1:
        if len(layer) % 2 == 1:
            layer.append(layer[-1])
        next_layer = []
        for i in range(0, len(layer), 2):
            combined = f"{layer[i]}{layer[i + 1]}".encode("utf-8")
            next_layer.append(hashlib.sha256(combined).hexdigest())
        layer = next_layer
    return layer[0]


def build_ledger_anchor(db: Session) -> dict:
    verify = verify_ledger_chain(db)
    records = (
        db.query(LedgerRecord)
        .filter(LedgerRecord.record_hash.isnot(None))
        .order_by(LedgerRecord.created_at.asc(), LedgerRecord.id.asc())
        .all()
    )
    hashes = [record.record_hash for record in records if record.record_hash]
    root = merkle_root(hashes)
    anchor = {
        "spec_version": get_rewards_config().get("spec_version", "0.1"),
        "anchor_type": "pocp_ledger_merkle_root",
        "node_id": os.getenv("POCP_NODE_ID", "unknown"),
        "anchored_at": datetime.now(timezone.utc).isoformat(),
        "record_count": len(hashes),
        "merkle_root": root,
        "ledger_valid": verify["valid"],
        "ledger_record_count": verify["count"],
        "tip_hash": hashes[-1] if hashes else None,
    }

    public_key = get_node_public_key_hex()
    if public_key:
        signature = sign_message(root)
        if signature:
            anchor["federation"] = {
                "public_key": public_key,
                "signature": signature,
                "signed_field": "merkle_root",
            }

    return anchor
