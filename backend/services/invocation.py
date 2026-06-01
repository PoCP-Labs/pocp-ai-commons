"""Record and query Human → Agent → Skill → LLM invocation chains."""

from sqlalchemy.orm import Session

from intelligence.entity_ontology import validate_invocation_edge
from models.entity import Entity, EntityType
from models.invocation import InvocationStatus, InvocationStep, InvocationTrace


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
    initiator = db.query(Entity).filter(Entity.id == initiator_id).first()
    if not initiator:
        raise ValueError("Initiator entity not found")
    if initiator.entity_type != EntityType.human:
        raise ValueError("Initiator must be a human entity")

    skill_entity = db.query(Entity).filter(Entity.id == skill_entity_id).first()
    if not skill_entity or skill_entity.entity_type != EntityType.skill:
        raise ValueError("Skill entity not found")

    trace = InvocationTrace(
        initiator_id=initiator_id,
        task_id=task_id,
        contribution_id=contribution_id,
        model_provider=model_provider,
        status=InvocationStatus.completed,
    )
    db.add(trace)
    db.flush()

    steps: list[InvocationStep] = []
    order = 1

    if agent_entity_id:
        agent_entity = db.query(Entity).filter(Entity.id == agent_entity_id).first()
        if not agent_entity or agent_entity.entity_type != EntityType.agent:
            raise ValueError("Agent entity not found")
        steps.append(
            InvocationStep(
                trace_id=trace.id,
                step_order=order,
                source_entity_id=initiator_id,
                target_entity_id=agent_entity_id,
                action="uses",
            )
        )
        order += 1
        steps.append(
            InvocationStep(
                trace_id=trace.id,
                step_order=order,
                source_entity_id=agent_entity_id,
                target_entity_id=skill_entity_id,
                action="calls",
            )
        )
        order += 1
    else:
        steps.append(
            InvocationStep(
                trace_id=trace.id,
                step_order=order,
                source_entity_id=initiator_id,
                target_entity_id=skill_entity_id,
                action="uses",
            )
        )
        order += 1

    for s in steps:
        _assert_step_edge(db, s.source_entity_id, s.target_entity_id, s.action)
        db.add(s)

    db.flush()
    return trace
