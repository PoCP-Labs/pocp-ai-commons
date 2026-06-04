"""Metered entity-dialogue invoke → capability_execute with CapabilityReceipt.

PL-2: dialogue `invoke` with `payload.execute=true` runs execute_skill / execute_agent,
embeds pocp.capability_receipt.v0.1 on trace steps, and returns agent receipt metadata.
"""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from models.entity import Entity, EntityType
from models.invocation import InvocationStep, InvocationTrace
from services.capability_execute import attach_receipt_to_result, execute_agent, execute_skill
from services.capability_receipt import build_capability_receipt, build_step_capability_receipts
from services.entity_local_chain import find_elc_record_for_exchange


def _dialogue_user_input(payload: dict[str, Any]) -> str:
    raw = payload.get("input")
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    if isinstance(raw, dict):
        for key in ("topic", "prompt", "query", "text"):
            val = raw.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
        return str(raw)
    if isinstance(payload.get("prompt"), str):
        return payload["prompt"].strip()
    return "Execute via PoCP entity dialogue"


def _require_dialogue_exchange_id(
    db: Session,
    *,
    consumer_entity_id: str,
    execution: dict[str, Any],
) -> str:
    """CIP-P1.2: metered dialogue invoke must emit exchange_id visible on ELC."""
    billing = execution.get("billing") if isinstance(execution.get("billing"), dict) else {}
    exchange_id = billing.get("exchange_id")
    if not exchange_id:
        raise HTTPException(
            status_code=500,
            detail="Metered dialogue invoke must emit billing.exchange_id (exchange spine)",
        )
    if not find_elc_record_for_exchange(db, consumer_entity_id, str(exchange_id)):
        raise HTTPException(
            status_code=500,
            detail=(
                f"exchange_id {exchange_id} not found in entity local chain "
                f"for {consumer_entity_id}"
            ),
        )
    execution["exchange_id"] = exchange_id
    return str(exchange_id)


def tag_trace_dialogue(
    db: Session,
    trace_id: str,
    *,
    dialogue_id: str | None,
    dialogue_kind: str = "invoke",
) -> None:
    trace = (
        db.query(InvocationTrace)
        .options(joinedload(InvocationTrace.steps))
        .filter(InvocationTrace.id == trace_id)
        .first()
    )
    if not trace:
        return
    for step in trace.steps:
        meta = dict(step.metadata_ or {})
        if dialogue_id:
            meta["dialogue_id"] = dialogue_id
        meta["dialogue_kind"] = dialogue_kind
        step.metadata_ = meta
    db.flush()


def embed_capability_receipts_on_trace(
    db: Session,
    trace_id: str,
    *,
    request_summary: str | None = None,
    response_summary: str | None = None,
) -> list[dict[str, Any]]:
    """Stamp each InvocationStep with pocp.capability_receipt.v0.1 in metadata."""
    trace = (
        db.query(InvocationTrace)
        .options(joinedload(InvocationTrace.steps))
        .filter(InvocationTrace.id == trace_id)
        .first()
    )
    if not trace:
        return []

    entity_ids = {s.target_entity_id for s in trace.steps} | {s.source_entity_id for s in trace.steps}
    entities = {
        e.id: e
        for e in db.query(Entity).filter(Entity.id.in_(entity_ids)).all()
    }
    receipts = build_step_capability_receipts(trace.id, list(trace.steps), entities)
    for step, receipt in zip(sorted(trace.steps, key=lambda s: s.step_order), receipts):
        if request_summary and step.action in ("uses", "calls"):
            receipt = build_capability_receipt(
                trace_id=trace.id,
                step=step,
                target_entity=entities.get(step.target_entity_id),
                request_summary=request_summary,
                response_summary=response_summary if step.action == "invokes_llm" else None,
                extra=step.metadata_ or {},
            )
        elif response_summary and step.action == "invokes_llm":
            receipt = build_capability_receipt(
                trace_id=trace.id,
                step=step,
                target_entity=entities.get(step.target_entity_id),
                response_summary=response_summary,
                extra=step.metadata_ or {},
            )
        meta = dict(step.metadata_ or {})
        meta["capability_receipt"] = receipt
        step.metadata_ = meta
    db.flush()
    return receipts


async def execute_metered_dialogue_invoke(
    db: Session,
    *,
    source: Entity,
    target: Entity,
    payload: dict[str, Any],
    refs_in: dict[str, Any],
    dialogue_id: str | None = None,
) -> dict[str, Any]:
    """Run metered capability_execute for dialogue invoke; attach CapabilityReceipt."""
    if source.entity_type != EntityType.human:
        raise HTTPException(
            status_code=400,
            detail="payload.execute requires from entity to be human (billing anchor)",
        )

    user_input = _dialogue_user_input(payload)
    common = {
        "human_entity_id": source.id,
        "user_input": user_input,
        "context": payload.get("context"),
        "llm_entity_id": payload.get("llm_entity_id"),
        "llm_provider": payload.get("llm_provider"),
        "task_id": refs_in.get("task_id"),
        "contribution_id": refs_in.get("contribution_id"),
    }

    if target.entity_type == EntityType.skill:
        execution = await execute_skill(
            db,
            skill_entity_id=target.id,
            agent_entity_id=payload.get("agent_entity_id"),
            llm_model=payload.get("llm_model"),
            **common,
        )
    elif target.entity_type == EntityType.agent:
        execution = await execute_agent(
            db,
            agent_entity_id=target.id,
            skill_entity_id=payload.get("skill_entity_id"),
            submit_contribution=bool(payload.get("submit_contribution")),
            **common,
        )
    else:
        raise HTTPException(
            status_code=400,
            detail=(
                f"payload.execute not supported for target type {target.entity_type.value}; "
                "use skill or agent, or omit execute for trace-only"
            ),
        )

    trace_id = execution.get("trace_id")
    if trace_id:
        tag_trace_dialogue(db, trace_id, dialogue_id=dialogue_id)
        output_text = str(execution.get("output") or "")
        capability_receipts = embed_capability_receipts_on_trace(
            db,
            trace_id,
            request_summary=user_input,
            response_summary=output_text[:8000] if output_text else None,
        )
        execution["capability_receipts"] = capability_receipts
        attach_receipt_to_result(db, execution)

    if execution.get("trace_id"):
        _require_dialogue_exchange_id(
            db,
            consumer_entity_id=source.id,
            execution=execution,
        )

    return execution
