"""Record and query Human → Agent → Skill → LLM invocation chains (INVOCATION-SCHEMA-v0.3)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session, joinedload

from intelligence.entity_ontology import validate_invocation_edge
from models.entity import Entity, EntityType
from models.invocation import InvocationStatus, InvocationStep, InvocationTrace

INVOCATION_TRACE_SPEC = "pocp.invocation_trace.v0.3"

# Trace lifecycle — aligned with INVOCATION-SCHEMA-v0.3 (started | completed | failed).
INVOCATION_TRACE_TRANSITIONS: dict[InvocationStatus, frozenset[InvocationStatus]] = {
    InvocationStatus.started: frozenset({InvocationStatus.completed, InvocationStatus.failed}),
    InvocationStatus.completed: frozenset(),
    InvocationStatus.failed: frozenset(),
}


def _assert_step_edge(db: Session, source_id: str, target_id: str, action: str) -> None:
    source = db.query(Entity).filter(Entity.id == source_id).first()
    target = db.query(Entity).filter(Entity.id == target_id).first()
    if not source or not target:
        return
    validate_invocation_edge(
        source.entity_type.value,
        target.entity_type.value,
        action,
        strict=True,
    )


def _assert_trace_transition(current: InvocationStatus, target: InvocationStatus) -> None:
    allowed = INVOCATION_TRACE_TRANSITIONS.get(current, frozenset())
    if target not in allowed and target != current:
        raise ValueError(f"Invalid trace status transition: {current.value} -> {target.value}")


def step_to_v03_dict(step: InvocationStep) -> dict[str, Any]:
    return {
        "step_order": step.step_order,
        "source_entity_id": step.source_entity_id,
        "target_entity_id": step.target_entity_id,
        "action": step.action,
        "metadata": dict(step.metadata_ or {}),
    }


def trace_to_v03_dict(trace: InvocationTrace) -> dict[str, Any]:
    """Export trace envelope per INVOCATION-SCHEMA-v0.3."""
    steps = sorted(trace.steps, key=lambda s: s.step_order)
    return {
        "spec_version": INVOCATION_TRACE_SPEC,
        "invocation_id": trace.id,
        "initiator_entity_id": trace.initiator_id,
        "task_id": trace.task_id,
        "contribution_id": trace.contribution_id,
        "model_provider": trace.model_provider,
        "status": trace.status.value,
        "steps": [step_to_v03_dict(s) for s in steps],
        "created_at": trace.created_at.isoformat() if trace.created_at else None,
    }


def get_invocation_trace(db: Session, trace_id: str) -> InvocationTrace | None:
    db.expire_all()
    return (
        db.query(InvocationTrace)
        .options(joinedload(InvocationTrace.steps))
        .filter(InvocationTrace.id == trace_id)
        .first()
    )


def start_invocation_trace(
    db: Session,
    *,
    initiator_id: str,
    model_provider: str = "deepseek",
    task_id: str | None = None,
    contribution_id: str | None = None,
) -> InvocationTrace:
    initiator = db.query(Entity).filter(Entity.id == initiator_id).first()
    if not initiator:
        raise ValueError("Initiator entity not found")
    if initiator.entity_type != EntityType.human:
        raise ValueError("Initiator must be a human entity")

    trace = InvocationTrace(
        initiator_id=initiator_id,
        task_id=task_id,
        contribution_id=contribution_id,
        model_provider=model_provider,
        status=InvocationStatus.started,
    )
    db.add(trace)
    db.flush()
    return trace


def add_invocation_step(
    db: Session,
    trace_id: str,
    *,
    source_entity_id: str,
    target_entity_id: str,
    action: str,
    step_order: int | None = None,
    metadata: dict[str, Any] | None = None,
) -> InvocationStep:
    trace = get_invocation_trace(db, trace_id)
    if trace is None:
        raise ValueError("Invocation trace not found")
    if trace.status != InvocationStatus.started:
        raise ValueError(f"Cannot add steps to trace in status {trace.status.value}")

    order = step_order
    if order is None:
        order = len(trace.steps) + 1

    _assert_step_edge(db, source_entity_id, target_entity_id, action)
    step = InvocationStep(
        trace_id=trace_id,
        step_order=order,
        source_entity_id=source_entity_id,
        target_entity_id=target_entity_id,
        action=action,
        metadata_=dict(metadata or {}),
    )
    db.add(step)
    db.flush()
    return step


def transition_invocation_trace(
    db: Session,
    trace_id: str,
    *,
    status: str,
) -> InvocationTrace:
    trace = get_invocation_trace(db, trace_id)
    if trace is None:
        raise ValueError("Invocation trace not found")
    try:
        target = InvocationStatus(status)
    except ValueError as exc:
        raise ValueError(f"Invalid status: {status}") from exc
    _assert_trace_transition(trace.status, target)
    trace.status = target
    db.flush()
    return trace


def complete_invocation_trace(db: Session, trace_id: str) -> InvocationTrace:
    return transition_invocation_trace(db, trace_id, status=InvocationStatus.completed.value)


def fail_invocation_trace(
    db: Session,
    trace_id: str,
    *,
    reason: str | None = None,
) -> InvocationTrace:
    trace = transition_invocation_trace(db, trace_id, status=InvocationStatus.failed.value)
    if reason and trace.steps:
        last = trace.steps[-1]
        meta = dict(last.metadata_ or {})
        meta["failure_reason"] = reason
        last.metadata_ = meta
        db.flush()
    return trace


def record_invocation(
    db: Session,
    *,
    initiator_id: str,
    skill_entity_id: str,
    agent_entity_id: str | None = None,
    model_provider: str = "deepseek",
    task_id: str | None = None,
    contribution_id: str | None = None,
) -> InvocationTrace:
    """Legacy human→agent→skill path — starts trace, records steps, completes (v0.3 SM)."""
    initiator = db.query(Entity).filter(Entity.id == initiator_id).first()
    if not initiator:
        raise ValueError("Initiator entity not found")
    if initiator.entity_type != EntityType.human:
        raise ValueError("Initiator must be a human entity")

    skill_entity = db.query(Entity).filter(Entity.id == skill_entity_id).first()
    if not skill_entity or skill_entity.entity_type != EntityType.skill:
        raise ValueError("Skill entity not found")

    trace = start_invocation_trace(
        db,
        initiator_id=initiator_id,
        model_provider=model_provider,
        task_id=task_id,
        contribution_id=contribution_id,
    )

    if agent_entity_id:
        agent_entity = db.query(Entity).filter(Entity.id == agent_entity_id).first()
        if not agent_entity or agent_entity.entity_type != EntityType.agent:
            raise ValueError("Agent entity not found")
        add_invocation_step(
            db,
            trace.id,
            source_entity_id=initiator_id,
            target_entity_id=agent_entity_id,
            action="uses",
            step_order=1,
        )
        add_invocation_step(
            db,
            trace.id,
            source_entity_id=agent_entity_id,
            target_entity_id=skill_entity_id,
            action="calls",
            step_order=2,
        )
    else:
        add_invocation_step(
            db,
            trace.id,
            source_entity_id=initiator_id,
            target_entity_id=skill_entity_id,
            action="uses",
            step_order=1,
        )

    complete_invocation_trace(db, trace.id)
    return get_invocation_trace(db, trace.id) or trace
