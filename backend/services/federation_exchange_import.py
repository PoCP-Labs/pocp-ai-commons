"""Federation L1 import for portable exchange proofs (metadata + verify, no BC mint)."""

from __future__ import annotations

import os
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from models.entity import Entity
from models.federation import FederatedImport
from models.wallet import ReputationScore
from schemas.federation import TrustedNode
from services.entity_portable import resolve_or_create_portable_entity
from services.exchange_proof import compute_exchange_proof_hash, verify_exchange_proof_integrity
from services.federation_import import _add_reputation, _trust_weight
from services.ledger_chain import append_ledger_record
from services.trust_config import trusted_nodes_map as _trusted_nodes_map

ACCEPTANCE_LEVELS = frozenset({"L0", "L1", "L2", "L3"})
DEFAULT_ACCEPTANCE = "L1"


def _verify_exchange_proof_signature(
    source_node_id: str,
    proof: dict,
    trusted: dict[str, TrustedNode],
) -> None:
    require_sig = os.getenv("POCP_REQUIRE_IMPORT_SIGNATURE", "false").lower() == "true"
    federation = proof.get("federation") or {}
    has_sig = bool(
        federation.get("signature")
        or (federation.get("signatures") or {}).get("classic")
        or (federation.get("signatures") or {}).get("pqc")
    )
    if not has_sig and not require_sig:
        return
    if not has_sig:
        raise HTTPException(status_code=400, detail="Exchange proof federation signature required")

    from services.crypto_suite import federation_signatures_valid

    proof_hash = (proof.get("integrity") or {}).get("proof_hash")
    if not proof_hash:
        raise HTTPException(status_code=400, detail="Exchange proof missing integrity.proof_hash")
    if proof_hash != compute_exchange_proof_hash(proof):
        raise HTTPException(status_code=400, detail="Exchange proof hash mismatch")

    node = trusted.get(source_node_id)
    public_key = federation.get("public_key") or (node.public_key if node else None)
    pqc_public_key = (node.pqc_public_key if node else None) or None
    if not federation_signatures_valid(
        federation,
        proof_hash,
        trusted_public_key=public_key,
        trusted_pqc_public_key=pqc_public_key,
    ):
        raise HTTPException(status_code=400, detail="Invalid exchange proof signature")


def import_federated_exchange_proof(
    db: Session,
    source_node_id: str,
    proof: dict[str, Any],
    *,
    acceptance_level: str = DEFAULT_ACCEPTANCE,
) -> FederatedImport:
    """L1: verify exchange proof, record import, optional advisory reputation — no BC mint."""
    level = (acceptance_level or DEFAULT_ACCEPTANCE).upper()
    if level not in ACCEPTANCE_LEVELS:
        raise HTTPException(status_code=400, detail=f"acceptance_level must be one of {sorted(ACCEPTANCE_LEVELS)}")

    allow_untrusted = os.getenv("POCP_ALLOW_UNTRUSTED_IMPORT", "false").lower() == "true"
    trusted = _trusted_nodes_map()
    if source_node_id not in trusted and not allow_untrusted:
        raise HTTPException(status_code=403, detail=f"Untrusted source node: {source_node_id}")

    verification = verify_exchange_proof_integrity(proof)
    if not verification.get("valid"):
        raise HTTPException(
            status_code=400,
            detail={"message": "Exchange proof verification failed", "checks": verification.get("checks")},
        )

    _verify_exchange_proof_signature(source_node_id, proof, trusted)

    exchange_id = proof.get("exchange_id") or (proof.get("exchange") or {}).get("exchange_id")
    if not exchange_id:
        raise HTTPException(status_code=400, detail="Exchange proof missing exchange_id")

    source_key = f"exchange:{exchange_id}"
    duplicate = (
        db.query(FederatedImport)
        .filter(
            FederatedImport.source_node_id == source_node_id,
            FederatedImport.source_contribution_id == source_key,
        )
        .first()
    )
    if duplicate:
        return duplicate

    exchange = proof.get("exchange") or {}
    consumer = (proof.get("entities") or {}).get("consumer") or {}
    portable_id = consumer.get("portable_id") or f"pocp:exchange:{exchange_id}"
    primary = resolve_or_create_portable_entity(db, portable_id)

    ledger_record = proof.get("ledger_record") or {}
    ledger_hash = ledger_record.get("record_hash")
    receipt_hash = exchange.get("receipt_hash") or (proof.get("integrity") or {}).get("receipt_hash") or ""

    trust_weight = _trust_weight(source_node_id)
    reputation_applied = 0.0
    if level in ("L1", "L2", "L3"):
        reputation_applied = round(0.1 * trust_weight, 4)
        if reputation_applied > 0:
            _add_reputation(
                db,
                primary.id,
                reputation_applied,
                "federated_exchange",
                reference_id=source_key,
            )

    record = FederatedImport(
        source_node_id=source_node_id,
        source_contribution_id=source_key,
        primary_entity_id=primary.id,
        primary_portable_id=portable_id,
        task_title=f"Exchange {exchange_id}",
        contribution_type="exchange",
        evidence_hash=receipt_hash[:64] if receipt_hash else exchange_id[:64],
        ledger_record_hash=ledger_hash,
        trust_weight=trust_weight,
        reputation_applied=reputation_applied,
        payload={
            "import_kind": "exchange_proof",
            "acceptance_level": level,
            "exchange_id": exchange_id,
            "exchange_kind": exchange.get("exchange_kind"),
            "proof_id": proof.get("proof_id"),
            "verification_checks": verification.get("checks"),
        },
    )
    db.add(record)
    db.flush()

    append_ledger_record(
        db,
        contribution_id=None,
        event_type="federation_exchange_import",
        payload={
            "federated_import_id": record.id,
            "source_node_id": source_node_id,
            "exchange_id": exchange_id,
            "acceptance_level": level,
            "primary_entity_id": primary.id,
            "receipt_hash": receipt_hash,
            "ledger_record_hash": ledger_hash,
            "trust_weight": trust_weight,
            "reputation_applied": reputation_applied,
        },
    )
    db.flush()
    return record
