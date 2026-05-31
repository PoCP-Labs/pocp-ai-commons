"""Signed agent action receipts (GARL / RECEIPT-inspired, off-chain).

Each invocation trace can export a hash-linked, Ed25519-signed receipt for
verifiable agent work without requiring on-chain settlement.
See docs/EXTERNAL-INTEGRATIONS.md
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from sqlalchemy.orm import Session, joinedload

from models.invocation import InvocationTrace
from services.capability_receipt import build_step_capability_receipts
from services.federation_crypto import get_node_public_key_hex, sign_message, verify_message

RECEIPT_SPEC_VERSION = "pocp.agent_receipt.v0.1"
RECEIPT_COMPAT = ["garl-receipt-v0", "receipt-chain-v0"]


def _jsonable(value: Any) -> Any:
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, list):
        return [_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    return value


def build_receipt_payload(trace: InvocationTrace) -> dict:
    return {
        "spec_version": RECEIPT_SPEC_VERSION,
        "compat": RECEIPT_COMPAT,
        "trace_id": trace.id,
        "initiator_id": trace.initiator_id,
        "task_id": trace.task_id,
        "contribution_id": trace.contribution_id,
        "model_provider": trace.model_provider,
        "status": trace.status.value,
        "created_at": trace.created_at,
        "steps": [
            {
                "step_order": step.step_order,
                "source_entity_id": step.source_entity_id,
                "target_entity_id": step.target_entity_id,
                "action": step.action,
                "metadata": step.metadata_ or {},
            }
            for step in trace.steps
        ],
        "capability_receipts": build_step_capability_receipts(trace.id, list(trace.steps), {}),
    }


def compute_receipt_hash(payload: dict) -> str:
    material = json.dumps(_jsonable(payload), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def build_agent_receipt(trace: InvocationTrace) -> dict:
    payload = build_receipt_payload(trace)
    receipt_hash = compute_receipt_hash(payload)
    signature = sign_message(receipt_hash)
    public_key = get_node_public_key_hex()
    return {
        **payload,
        "integrity": {
            "hash_algorithm": "sha256",
            "receipt_hash": receipt_hash,
            "signature": signature,
            "signer_public_key": public_key,
            "signed": signature is not None and public_key is not None,
        },
        "share_url_hint": f"/api/v1/invocations/{trace.id}/receipt",
    }


def verify_agent_receipt(receipt: dict) -> bool:
    integrity = receipt.get("integrity") or {}
    receipt_hash = integrity.get("receipt_hash")
    signature = integrity.get("signature")
    public_key = integrity.get("signer_public_key")
    if not receipt_hash or not signature or not public_key:
        return False
    payload = {k: v for k, v in receipt.items() if k != "integrity" and k != "share_url_hint"}
    expected = compute_receipt_hash(payload)
    if expected != receipt_hash:
        return False
    return verify_message(receipt_hash, signature, public_key)


def load_trace_for_receipt(db: Session, trace_id: str) -> InvocationTrace | None:
    return (
        db.query(InvocationTrace)
        .options(joinedload(InvocationTrace.steps))
        .filter(InvocationTrace.id == trace_id)
        .first()
    )
