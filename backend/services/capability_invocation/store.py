"""Persistent capability invocation ledger — PR-07."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from models.capability import EntityCapability
from models.capability_invocation import (
    CAPABILITY_INVOCATION_TRANSITIONS,
    CapabilityInvocationRecord,
    CapabilityInvocationStatus,
)
from models.entity import Entity
from services.invocation_ledger import build_invocation_ref


def hash_payload(payload: dict[str, Any] | str | bytes) -> str:
    if isinstance(payload, dict):
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    elif isinstance(payload, bytes):
        raw = payload.decode("utf-8", errors="replace")
    else:
        raw = str(payload)
    return f"sha256:{hashlib.sha256(raw.encode()).hexdigest()}"


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _new_invocation_id() -> str:
    return f"invoke_{uuid.uuid4().hex[:16]}"


def _assert_transition(current: CapabilityInvocationStatus, target: CapabilityInvocationStatus) -> None:
    allowed = CAPABILITY_INVOCATION_TRANSITIONS.get(current, frozenset())
    if target not in allowed and target != current:
        raise ValueError(f"Invalid status transition: {current.value} -> {target.value}")


def record_to_dict(record: CapabilityInvocationRecord) -> dict[str, Any]:
    return {
        "invocation_id": record.id,
        "task_id": record.task_id,
        "caller_entity_id": record.caller_entity_id,
        "callee_entity_id": record.callee_entity_id,
        "capability_id": record.capability_id,
        "input_hash": record.input_hash,
        "output_hash": record.output_hash,
        "cost_unit": record.cost_unit,
        "cost_amount": float(record.cost_amount or 0),
        "status": record.status.value,
        "trace_id": record.trace_id,
        "exchange_id": record.exchange_id,
        "metadata": dict(record.metadata_ or {}),
        "created_at": record.created_at.isoformat() if record.created_at else None,
        "updated_at": record.updated_at.isoformat() if record.updated_at else None,
    }


def invocation_ref_from_record(record: CapabilityInvocationRecord) -> dict[str, Any]:
    """Normalized invocation_ref for exchange_settled from capability invocation row."""
    meta = record.metadata_ or {}
    return build_invocation_ref(
        invocation_id=record.id,
        source_entity_id=record.caller_entity_id,
        target_entity_id=record.callee_entity_id,
        trace_id=record.trace_id,
        capability_id=record.capability_id,
        capability=meta.get("capability_type"),
        usage={
            "cost_unit": record.cost_unit,
            "cost_amount": float(record.cost_amount or 0),
            "input_hash": record.input_hash,
            "output_hash": record.output_hash,
            "capability_invocation_id": record.id,
        },
        receipt_hash=record.output_hash or record.input_hash,
        settlement_ref=record.exchange_id,
        status=record.status.value if record.status == CapabilityInvocationStatus.settled else "completed",
        timestamp=record.updated_at or record.created_at,
    )


def create_capability_invocation(
    db: Session,
    *,
    caller_entity_id: str,
    callee_entity_id: str,
    capability_id: str,
    input_payload: dict[str, Any] | str | bytes | None = None,
    input_hash: str | None = None,
    task_id: str | None = None,
    trace_id: str | None = None,
    cost_unit: str | None = None,
    cost_amount: float = 0.0,
    metadata: dict[str, Any] | None = None,
    invocation_id: str | None = None,
) -> CapabilityInvocationRecord:
    if db.get(Entity, caller_entity_id) is None:
        raise ValueError(f"Caller entity not found: {caller_entity_id}")
    if db.get(Entity, callee_entity_id) is None:
        raise ValueError(f"Callee entity not found: {callee_entity_id}")
    cap = db.get(EntityCapability, capability_id)
    if cap is None:
        raise ValueError(f"Capability not found: {capability_id}")

    ih = input_hash or (hash_payload(input_payload) if input_payload is not None else hash_payload(""))
    inv_id = invocation_id or _new_invocation_id()
    if len(inv_id) > 36:
        inv_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{caller_entity_id}:{capability_id}:{ih}"))

    record = CapabilityInvocationRecord(
        id=inv_id,
        task_id=task_id,
        caller_entity_id=caller_entity_id,
        callee_entity_id=callee_entity_id,
        capability_id=capability_id,
        input_hash=ih,
        cost_unit=cost_unit,
        cost_amount=float(cost_amount or 0),
        trace_id=trace_id,
        metadata_={
            **(metadata or {}),
            "capability_type": cap.capability_type.value,
        },
        status=CapabilityInvocationStatus.created,
    )
    db.add(record)
    db.flush()
    return record


def transition_capability_invocation(
    db: Session,
    invocation_id: str,
    *,
    status: str,
) -> CapabilityInvocationRecord:
    record = db.get(CapabilityInvocationRecord, invocation_id)
    if record is None:
        raise ValueError("Invocation not found")
    try:
        target = CapabilityInvocationStatus(status)
    except ValueError as exc:
        raise ValueError(f"Invalid status: {status}") from exc
    _assert_transition(record.status, target)
    record.status = target
    record.updated_at = _now()
    db.flush()
    return record


def complete_capability_invocation(
    db: Session,
    invocation_id: str,
    *,
    output_payload: dict[str, Any] | str | bytes | None = None,
    output_hash: str | None = None,
) -> CapabilityInvocationRecord:
    record = db.get(CapabilityInvocationRecord, invocation_id)
    if record is None:
        raise ValueError("Invocation not found")
    if record.status not in (
        CapabilityInvocationStatus.created,
        CapabilityInvocationStatus.accepted,
        CapabilityInvocationStatus.running,
    ):
        raise ValueError(f"Cannot complete invocation in status {record.status.value}")
    oh = output_hash or (hash_payload(output_payload) if output_payload is not None else None)
    if not oh:
        raise ValueError("output_hash or output_payload required")
    record.output_hash = oh
    record.status = CapabilityInvocationStatus.completed
    record.updated_at = _now()
    db.flush()
    return record


def link_capability_invocation_settlement(
    db: Session,
    invocation_id: str,
    *,
    exchange_id: str,
    status: str = "settled",
) -> CapabilityInvocationRecord:
    record = db.get(CapabilityInvocationRecord, invocation_id)
    if record is None:
        raise ValueError("Invocation not found")
    target = CapabilityInvocationStatus(status)
    if target == CapabilityInvocationStatus.settled:
        if record.status in (
            CapabilityInvocationStatus.created,
            CapabilityInvocationStatus.accepted,
            CapabilityInvocationStatus.running,
        ):
            if not record.output_hash:
                record.output_hash = record.input_hash
            record.status = CapabilityInvocationStatus.completed
        _assert_transition(record.status, CapabilityInvocationStatus.settled)
    else:
        _assert_transition(record.status, target)
    record.exchange_id = exchange_id
    record.status = target
    record.updated_at = _now()
    db.flush()
    return record


def get_capability_invocation(db: Session, invocation_id: str) -> CapabilityInvocationRecord | None:
    return db.get(CapabilityInvocationRecord, invocation_id)


def list_capability_invocations(
    db: Session,
    *,
    caller_entity_id: str | None = None,
    callee_entity_id: str | None = None,
    capability_id: str | None = None,
    status: str | None = None,
    limit: int = 50,
) -> list[CapabilityInvocationRecord]:
    query = db.query(CapabilityInvocationRecord)
    if caller_entity_id:
        query = query.filter(CapabilityInvocationRecord.caller_entity_id == caller_entity_id)
    if callee_entity_id:
        query = query.filter(CapabilityInvocationRecord.callee_entity_id == callee_entity_id)
    if capability_id:
        query = query.filter(CapabilityInvocationRecord.capability_id == capability_id)
    if status:
        query = query.filter(CapabilityInvocationRecord.status == CapabilityInvocationStatus(status))
    return (
        query.order_by(CapabilityInvocationRecord.updated_at.desc()).limit(min(limit, 200)).all()
    )
