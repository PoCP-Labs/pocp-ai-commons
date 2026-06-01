"""Invocation ledger normalization — canonical invocation_ref and chain digests."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session, joinedload

from models.invocation import InvocationTrace

INVOCATION_REF_SPEC = "pocp.invocation_ref.v0.1"

REQUIRED_INVOCATION_REF_FIELDS = (
    "invocation_id",
    "source_entity_id",
    "target_entity_id",
    "receipt_hash",
    "settlement_ref",
    "status",
    "timestamp",
)


def _stable_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def build_invocation_ref(
    *,
    source_entity_id: str,
    target_entity_id: str,
    trace_id: str | None = None,
    invocation_id: str | None = None,
    capability_id: str | None = None,
    capability: str | None = None,
    usage: dict[str, Any] | None = None,
    receipt_hash: str | None = None,
    verification_ref: str | None = None,
    settlement_ref: str | None = None,
    status: str = "settled",
    timestamp: datetime | None = None,
) -> dict[str, Any]:
    """Build normalized invocation_ref for exchange_settled and proof export."""
    ts = timestamp or datetime.utcnow()
    inv_id = invocation_id or trace_id or f"inv_{uuid.uuid4().hex[:16]}"
    return {
        "spec_version": INVOCATION_REF_SPEC,
        "invocation_id": inv_id,
        "trace_id": trace_id,
        "source_entity_id": source_entity_id,
        "target_entity_id": target_entity_id,
        "capability_id": capability_id,
        "capability": capability,
        "usage": dict(usage or {}),
        "receipt_hash": receipt_hash,
        "verification_ref": verification_ref,
        "settlement_ref": settlement_ref,
        "status": status,
        "timestamp": ts.isoformat() if isinstance(ts, datetime) else str(ts),
    }


def compute_invocation_chain_digest(steps: list[dict[str, Any]]) -> str:
    """Digest of ordered invocation steps (operational layer chain)."""
    canonical = [
        {
            "step_order": step.get("step_order"),
            "source_entity_id": step.get("source_entity_id"),
            "target_entity_id": step.get("target_entity_id"),
            "action": step.get("action"),
        }
        for step in sorted(steps, key=lambda row: int(row.get("step_order") or 0))
    ]
    return hashlib.sha256(_stable_json({"steps": canonical}).encode()).hexdigest()


def compute_invocation_ref_digest(invocation_ref: dict[str, Any]) -> str:
    """Digest when no multi-step trace exists (flat exchange metering)."""
    stable = {
        k: invocation_ref.get(k)
        for k in (
            "invocation_id",
            "trace_id",
            "source_entity_id",
            "target_entity_id",
            "capability_id",
            "capability",
            "receipt_hash",
            "settlement_ref",
            "status",
        )
        if invocation_ref.get(k) is not None
    }
    return hashlib.sha256(_stable_json(stable).encode()).hexdigest()


def trace_chain_digest(db: Session, trace_id: str) -> str | None:
    trace = (
        db.query(InvocationTrace)
        .options(joinedload(InvocationTrace.steps))
        .filter(InvocationTrace.id == trace_id)
        .first()
    )
    if trace is None:
        return None
    steps = [
        {
            "step_order": step.step_order,
            "source_entity_id": step.source_entity_id,
            "target_entity_id": step.target_entity_id,
            "action": step.action,
        }
        for step in trace.steps
    ]
    return compute_invocation_chain_digest(steps)


def resolve_invocation_chain_digest(
    db: Session,
    invocation_ref: dict[str, Any] | None,
) -> str | None:
    if not invocation_ref:
        return None
    trace_id = invocation_ref.get("trace_id")
    if trace_id:
        digest = trace_chain_digest(db, trace_id)
        if digest:
            return digest
    return compute_invocation_ref_digest(invocation_ref)


def validate_invocation_ref(ref: dict[str, Any] | None) -> dict[str, Any]:
    """Validate normalized invocation_ref field presence."""
    if not ref:
        return {"valid": False, "missing": list(REQUIRED_INVOCATION_REF_FIELDS)}
    missing = [field for field in REQUIRED_INVOCATION_REF_FIELDS if not ref.get(field)]
    spec_ok = ref.get("spec_version") == INVOCATION_REF_SPEC
    return {
        "valid": spec_ok and not missing,
        "spec_version": ref.get("spec_version"),
        "missing": missing,
    }


def verify_exchange_invocation_chain(db: Session, exchange_id: str) -> dict[str, Any]:
    """Verify exchange_settled row carries invocation_ref linked to receipt and trace."""
    from services.entity_local_chain import find_exchange_ledger_record

    record = find_exchange_ledger_record(db, exchange_id)
    if record is None:
        return {"valid": False, "reason": "exchange_not_found", "exchange_id": exchange_id}

    payload = record.payload or {}
    invocation_ref = payload.get("invocation_ref") or {}
    checks: list[dict[str, Any]] = []
    valid = True

    ref_check = validate_invocation_ref(invocation_ref)
    checks.append({"check": "invocation_ref_fields", **ref_check})
    valid = valid and ref_check["valid"]

    receipt_hash = payload.get("receipt_hash")
    ref_receipt = invocation_ref.get("receipt_hash")
    receipt_ok = bool(receipt_hash) and receipt_hash == ref_receipt
    checks.append({"check": "receipt_hash_match", "valid": receipt_ok})
    valid = valid and receipt_ok

    settlement_ref = invocation_ref.get("settlement_ref")
    settlement_ok = settlement_ref == exchange_id
    checks.append(
        {
            "check": "settlement_ref",
            "valid": settlement_ok,
            "expected": exchange_id,
            "actual": settlement_ref,
        }
    )
    valid = valid and settlement_ok

    trace_id = invocation_ref.get("trace_id") or payload.get("invocation_trace_id")
    if trace_id:
        trace = db.query(InvocationTrace).filter(InvocationTrace.id == trace_id).first()
        trace_ok = trace is not None
        checks.append({"check": "trace_exists", "valid": trace_ok, "trace_id": trace_id})
        valid = valid and trace_ok

    chain_digest = resolve_invocation_chain_digest(db, invocation_ref)
    checks.append({"check": "invocation_chain_digest", "valid": bool(chain_digest), "digest": chain_digest})

    return {
        "valid": bool(valid and chain_digest),
        "exchange_id": exchange_id,
        "ledger_record_id": record.id,
        "invocation_ref": invocation_ref,
        "invocation_chain_digest": chain_digest,
        "checks": checks,
    }
