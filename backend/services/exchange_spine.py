"""Capability-first exchange spine — unified exchange_settled ledger events."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from models.ledger import LedgerRecord
from models.wallet import CreditTransaction
from services.invocation_ledger import build_invocation_ref
from services.ledger_chain import append_ledger_record
from services.settlement_policy import policy_tag

SPEC_VERSION = "pocp.exchange_spine.v0.1"

COMPUTE_CAPABILITIES = frozenset(
    {
        "gpu_inference",
        "training",
        "embeddings",
        "gpu",
        "compute",
    }
)


def new_exchange_id() -> str:
    return f"ex_{uuid.uuid4().hex[:16]}"


def infer_exchange_kind(
    *,
    capability: str | None = None,
    receipt: dict[str, Any] | None = None,
    skill_entity_id: str | None = None,
    service: str | None = None,
) -> str:
    """Return compute | capability | hybrid for exchange_settled payloads."""
    if skill_entity_id:
        return "hybrid"
    cap = (capability or (receipt or {}).get("capability") or service or "").lower()
    if cap in COMPUTE_CAPABILITIES or cap == "llm_inference":
        extra = (receipt or {}).get("extra") or {}
        usage = extra.get("usage") or {}
        metering = str(usage.get("metering_mode") or "").lower()
        if metering == "intel":
            return "capability"
        if cap == "llm_inference":
            return "compute"
        return "compute"
    return "capability"


def emit_exchange_settled(
    db: Session,
    *,
    consumer_entity_id: str,
    provider_entity_ids: list[str],
    exchange_kind: str,
    credit_transactions: list[CreditTransaction],
    receipt_hash: str | None = None,
    capability_id: str | None = None,
    capability: str | None = None,
    usage: dict[str, Any] | None = None,
    contribution_id: str | None = None,
    invocation_trace_id: str | None = None,
    invocation_ref: dict[str, Any] | None = None,
    legacy_event_type: str | None = None,
    settlement_policy: str = "compute_settlement.v1",
    settlement_policy_tag: dict[str, Any] | None = None,
    extra_payload: dict[str, Any] | None = None,
) -> LedgerRecord:
    """Append exchange_settled and bind credit_transactions via ledger_record_id."""
    exchange_id = new_exchange_id()
    providers = list(dict.fromkeys(pid for pid in provider_entity_ids if pid))

    bc_debited = sum(
        abs(float(tx.amount))
        for tx in credit_transactions
        if float(tx.amount) < 0
    )
    bc_credited = sum(
        float(tx.amount)
        for tx in credit_transactions
        if float(tx.amount) > 0
    )

    usage_block: dict[str, Any] = dict(usage or {})
    usage_block.setdefault("bc_debited", bc_debited)
    usage_block.setdefault("bc_credited", bc_credited)

    db.flush()
    tx_ids = [tx.id for tx in credit_transactions if tx.id]

    primary_provider = providers[0] if providers else consumer_entity_id
    normalized_ref = invocation_ref or build_invocation_ref(
        source_entity_id=consumer_entity_id,
        target_entity_id=primary_provider,
        trace_id=invocation_trace_id,
        capability_id=capability_id,
        capability=capability,
        usage=usage_block,
        receipt_hash=receipt_hash,
        verification_ref=receipt_hash,
        settlement_ref=exchange_id,
        status="settled",
    )
    if not normalized_ref.get("settlement_ref"):
        normalized_ref["settlement_ref"] = exchange_id
    if receipt_hash and not normalized_ref.get("receipt_hash"):
        normalized_ref["receipt_hash"] = receipt_hash
    if invocation_trace_id and not normalized_ref.get("trace_id"):
        normalized_ref["trace_id"] = invocation_trace_id

    policy_meta = settlement_policy_tag or policy_tag(settlement_policy)

    payload: dict[str, Any] = {
        "exchange_id": exchange_id,
        "exchange_kind": exchange_kind,
        "consumer_entity_id": consumer_entity_id,
        "provider_entity_ids": providers,
        "receipt_hash": receipt_hash,
        "capability_id": capability_id,
        "capability": capability,
        "usage": usage_block,
        "credit_transaction_ids": tx_ids,
        "settlement_policy": settlement_policy,
        "settlement_policy_id": policy_meta.get("settlement_policy_id"),
        "settlement_policy_version": policy_meta.get("settlement_policy_version"),
        "policy_hash": policy_meta.get("policy_hash"),
        "spec_version": SPEC_VERSION,
        "invocation_ref": normalized_ref,
    }
    if invocation_trace_id:
        payload["invocation_trace_id"] = invocation_trace_id
    if legacy_event_type:
        payload["legacy_event_type"] = legacy_event_type
    if extra_payload:
        payload.update(extra_payload)

    record = append_ledger_record(
        db,
        contribution_id=contribution_id,
        event_type="exchange_settled",
        payload=payload,
    )
    for tx in credit_transactions:
        tx.ledger_record_id = record.id
        db.add(tx)
    db.flush()
    return record


def link_transactions_to_ledger(
    db: Session,
    ledger_record_id: str,
    transactions: list[CreditTransaction],
) -> None:
    for tx in transactions:
        tx.ledger_record_id = ledger_record_id
        db.add(tx)
    db.flush()
