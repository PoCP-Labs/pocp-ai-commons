"""Portable exchange proof packets with ledger SPV inclusion."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import date, datetime
from typing import Any

from sqlalchemy.orm import Session

from models.entity import Entity
from models.ledger import LedgerRecord
from models.wallet import CreditTransaction, Wallet
from services.crypto_suite import active_crypto_suite, active_hash_algorithm, build_signature_block
from services.entity_local_chain import find_exchange_ledger_record
from services.federation_crypto import get_node_public_key_hex, sign_message
from services.invocation_ledger import resolve_invocation_chain_digest, validate_invocation_ref
from services.ledger_chain import _order_records_by_hash_chain
from services.ledger_merkle import build_inclusion_bundle
from services.crypto_suite import SUITE_V01_CLASSIC

POCP_EXCHANGE_PROOF_TYPE = "pocp_exchange_proof"
POCP_EXCHANGE_PROOF_SCHEMA = "pocp.exchange_proof.v0.1"
POCP_EXCHANGE_PROOF_SPEC_VERSION = "0.1"


def _jsonable(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, list):
        return [_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    return value


def _stable_hash(payload: dict) -> str:
    stable_payload = dict(payload)
    stable_payload.pop("generated_at", None)
    stable_payload.pop("federation", None)
    if isinstance(stable_payload.get("integrity"), dict):
        integrity = dict(stable_payload["integrity"])
        integrity.pop("proof_hash", None)
        stable_payload["integrity"] = integrity
    material = json.dumps(_jsonable(stable_payload), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def compute_exchange_proof_hash(proof: dict) -> str:
    return _stable_hash(proof)


def _entity_brief(entity: Entity | None) -> dict | None:
    if entity is None:
        return None
    return {
        "entity_id": entity.id,
        "entity_type": entity.entity_type.value,
        "name": entity.name,
        "portable_id": (entity.metadata_ or {}).get("portable_id"),
    }


def build_exchange_proof_packet(db: Session, exchange_id: str) -> dict | None:
    record = find_exchange_ledger_record(db, exchange_id)
    if record is None:
        return None

    payload = record.payload or {}
    consumer_id = payload.get("consumer_entity_id")
    provider_ids = payload.get("provider_entity_ids") or []
    invocation_ref = payload.get("invocation_ref") or {}
    invocation_chain_digest = resolve_invocation_chain_digest(db, invocation_ref)

    entity_ids = set(provider_ids)
    if consumer_id:
        entity_ids.add(consumer_id)
    entities = (
        {e.id: e for e in db.query(Entity).filter(Entity.id.in_(entity_ids)).all()}
        if entity_ids
        else {}
    )

    tx_ids = payload.get("credit_transaction_ids") or []
    transactions = []
    if tx_ids:
        rows = (
            db.query(CreditTransaction, Wallet)
            .join(Wallet, CreditTransaction.wallet_id == Wallet.id)
            .filter(CreditTransaction.id.in_(tx_ids))
            .all()
        )
        for tx, wallet in rows:
            transactions.append(
                {
                    "id": tx.id,
                    "entity_id": wallet.entity_id,
                    "amount": tx.amount,
                    "credit_type": tx.credit_type.value,
                    "reason": tx.reason,
                    "ledger_record_id": tx.ledger_record_id,
                    "created_at": tx.created_at,
                }
            )

    all_records = db.query(LedgerRecord).filter(LedgerRecord.record_hash.isnot(None)).all()
    ordered = _order_records_by_hash_chain(all_records)
    all_hashes = [r.record_hash for r in ordered if r.record_hash]
    exchange_inclusion = None
    if record.record_hash and all_hashes:
        exchange_inclusion = build_inclusion_bundle(all_hashes, record.record_hash)

    packet: dict[str, Any] = {
        "spec_version": POCP_EXCHANGE_PROOF_SPEC_VERSION,
        "proof_type": POCP_EXCHANGE_PROOF_TYPE,
        "proof_schema": POCP_EXCHANGE_PROOF_SCHEMA,
        "proof_id": f"pocp-exchange-proof:{exchange_id}",
        "generated_at": datetime.utcnow(),
        "exchange_id": exchange_id,
        "exchange": _jsonable(payload),
        "exchange_kind": payload.get("exchange_kind"),
        "entities": {
            "consumer": _entity_brief(entities.get(consumer_id)) if consumer_id else None,
            "providers": [_entity_brief(entities.get(pid)) for pid in provider_ids if pid in entities],
        },
        "credit_transactions": _jsonable(transactions),
        "ledger_record": {
            "id": record.id,
            "event_type": record.event_type,
            "record_hash": record.record_hash,
            "prev_hash": record.prev_hash,
            "created_at": record.created_at,
        },
        "exchange_inclusion": exchange_inclusion,
        "invocation_ref": _jsonable(invocation_ref),
        "invocation_chain_digest": invocation_chain_digest,
        "integrity": {
            "exchange_id": exchange_id,
            "ledger_record_hash": record.record_hash,
            "receipt_hash": payload.get("receipt_hash"),
            "invocation_ref_valid": validate_invocation_ref(invocation_ref).get("valid"),
            "crypto_suite": active_crypto_suite(),
            "hash_algorithm": active_hash_algorithm(),
            "canonicalization": "json-sort-keys-compact-excludes-generated_at-federation-proof_hash",
        },
    }

    packet["integrity"]["proof_hash"] = _stable_hash(packet)
    proof_hash = packet["integrity"]["proof_hash"]
    federation_block = build_signature_block(proof_hash, signed_field="integrity.proof_hash")
    if federation_block:
        packet["federation"] = federation_block
    elif get_node_public_key_hex():
        signature = sign_message(proof_hash)
        if signature:
            packet["federation"] = {
                "node_id": os.getenv("POCP_NODE_ID", "unknown"),
                "crypto_suite": SUITE_V01_CLASSIC,
                "public_key": get_node_public_key_hex(),
                "signature": signature,
                "signed_field": "integrity.proof_hash",
            }

    return _jsonable(packet)


def verify_exchange_proof_integrity(
    proof: dict[str, Any],
    *,
    trusted_public_key: str | None = None,
    require_signature: bool = False,
) -> dict[str, Any]:
    from services.ledger_merkle import verify_merkle_inclusion

    checks: list[dict[str, Any]] = []
    valid = True

    integrity = proof.get("integrity") or {}
    declared_hash = integrity.get("proof_hash")
    computed_hash = compute_exchange_proof_hash(proof)
    hash_ok = bool(declared_hash) and declared_hash == computed_hash
    checks.append({"check": "proof_hash", "valid": hash_ok, "declared": declared_hash, "computed": computed_hash})
    valid = valid and hash_ok

    ledger_record = proof.get("ledger_record") or {}
    inclusion = proof.get("exchange_inclusion") or {}
    leaf = inclusion.get("leaf_hash") or ledger_record.get("record_hash")
    if leaf and inclusion.get("merkle_root"):
        merkle_ok = verify_merkle_inclusion(
            leaf,
            inclusion.get("merkle_proof") or [],
            inclusion.get("merkle_root") or "",
        )
        checks.append(
            {
                "check": "exchange_inclusion",
                "valid": merkle_ok,
                "leaf_hash": leaf,
                "merkle_root": inclusion.get("merkle_root"),
            }
        )
        valid = valid and merkle_ok
    else:
        checks.append({"check": "exchange_inclusion", "valid": False, "reason": "missing_inclusion"})

    exchange = proof.get("exchange") or {}
    receipt_ok = bool(exchange.get("receipt_hash") or integrity.get("receipt_hash"))
    checks.append({"check": "receipt_hash_present", "valid": receipt_ok})
    valid = valid and receipt_ok

    invocation_ref = proof.get("invocation_ref") or exchange.get("invocation_ref") or {}
    ref_check = validate_invocation_ref(invocation_ref)
    checks.append({"check": "invocation_ref", **ref_check})
    valid = valid and ref_check.get("valid", False)

    chain_digest = proof.get("invocation_chain_digest")
    digest_ok = bool(chain_digest)
    checks.append({"check": "invocation_chain_digest", "valid": digest_ok, "digest": chain_digest})
    valid = valid and digest_ok

    federation = proof.get("federation") or {}
    sigs = federation.get("signatures") or {}
    has_sig = bool(federation.get("signature") or sigs.get("classic") or sigs.get("pqc"))
    if has_sig:
        from services.crypto_suite import federation_signatures_valid

        sig_ok = federation_signatures_valid(
            federation,
            declared_hash or computed_hash,
            trusted_public_key=trusted_public_key,
        )
        checks.append({"check": "federation_signature", "valid": sig_ok, "signed": True})
        valid = valid and sig_ok
    elif require_signature:
        checks.append({"check": "federation_signature", "valid": False, "signed": False})
        valid = False
    else:
        checks.append({"check": "federation_signature", "valid": True, "signed": False, "skipped": True})

    return {
        "valid": bool(valid),
        "proof_id": proof.get("proof_id"),
        "exchange_id": proof.get("exchange_id"),
        "checks": checks,
    }
