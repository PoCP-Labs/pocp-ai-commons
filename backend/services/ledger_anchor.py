"""Ledger Merkle root anchor for external verification."""

import os
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from models.ledger import LedgerRecord
from services.anchor_cosign import anchor_cosign_enabled, collect_peer_anchor_attestations
from services.federation_crypto import get_node_public_key_hex, sign_message
from services.crypto_suite import active_crypto_suite, active_hash_algorithm, build_signature_block
from services.graph import build_contribution_graph
from services.graph_merkle import build_graph_merkle_state
from services.ledger_chain import verify_ledger_chain
from services.ledger_merkle import build_inclusion_bundle, merkle_root
from services.protocol_config import get_rewards_config


def build_ledger_inclusion_proof(db: Session, record_hash: str) -> dict | None:
    """SPV inclusion proof for one ledger record against the live Merkle root."""
    records = (
        db.query(LedgerRecord)
        .filter(LedgerRecord.record_hash.isnot(None))
        .order_by(LedgerRecord.created_at.asc(), LedgerRecord.id.asc())
        .all()
    )
    hashes = [record.record_hash for record in records if record.record_hash]
    return build_inclusion_bundle(hashes, record_hash)


def build_ledger_anchor(db: Session, *, skip_cosign: bool = False) -> dict:
    verify = verify_ledger_chain(db)
    records = (
        db.query(LedgerRecord)
        .filter(LedgerRecord.record_hash.isnot(None))
        .order_by(LedgerRecord.created_at.asc(), LedgerRecord.id.asc())
        .all()
    )
    hashes = [record.record_hash for record in records if record.record_hash]
    root = merkle_root(hashes)
    graph_data = build_contribution_graph(db)
    graph_state = build_graph_merkle_state(graph_data["edges"])
    anchor = {
        "spec_version": get_rewards_config().get("spec_version", "0.1"),
        "anchor_type": "pocp_ledger_graph_merkle_root",
        "node_id": os.getenv("POCP_NODE_ID", "unknown"),
        "crypto_suite": active_crypto_suite(),
        "anchored_at": datetime.now(timezone.utc).isoformat(),
        "record_count": len(hashes),
        "merkle_root": root,
        "graph_merkle_root": graph_state["graph_merkle_root"],
        "graph_edge_count": graph_state["graph_edge_count"],
        "graph_algorithm": graph_state["algorithm"],
        "ledger_valid": verify["valid"],
        "ledger_record_count": verify["count"],
        "tip_hash": hashes[-1] if hashes else None,
        "hash_algorithm": active_hash_algorithm(),
    }

    public_key = get_node_public_key_hex()
    federation_block = build_signature_block(root, signed_field="merkle_root")
    if federation_block:
        anchor["federation"] = federation_block
    elif public_key:
        signature = sign_message(root)
        if signature:
            anchor["federation"] = {
                "public_key": public_key,
                "signature": signature,
                "signed_field": "merkle_root",
                "crypto_suite": active_crypto_suite(),
            }

    if anchor_cosign_enabled() and not skip_cosign:
        peer_attestations = collect_peer_anchor_attestations(
            root,
            anchor.get("tip_hash"),
            graph_merkle_root=anchor.get("graph_merkle_root"),
        )
        if peer_attestations:
            anchor["peer_attestations"] = peer_attestations
            anchor["cosign_summary"] = {
                "peer_count": len(peer_attestations),
                "node_ids": [p["node_id"] for p in peer_attestations],
                "model": "federated_merkle_cosign_v0.1",
            }

    return anchor
