"""StudyAgent service — wires graph runtime to InvocationTrace (NN-3)."""

from __future__ import annotations

import os

from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from genesis import LUMEN_0_ID
from models.contribution import (
    ContributionEvent,
    ContributionParticipant,
    ContributionStatus,
    ParticipantRole,
)
from models.entity import Entity, EntityType
from models.invocation import InvocationStatus, InvocationStep, InvocationTrace
from models.skill import Skill
from models.task import Task
from services.agent_runtimes.study_agent_runtime import run_study_agent_graph
from services.ai_chat import generate_ai_reply
from services.evidence import enrich_evidence


def _entity_by_name(db: Session, name: str, entity_type: EntityType) -> Entity | None:
    return (
        db.query(Entity)
        .filter(Entity.name == name, Entity.entity_type == entity_type)
        .first()
    )


def build_study_agent_evidence(run: dict) -> dict:
    """Portable evidence bundle linking draft to InvocationTrace (NN-3)."""
    draft = run.get("draft") or ""
    return {
        "content_preview": draft[:800],
        "study_agent": {
            "trace_id": run.get("trace_id"),
            "topic": run.get("topic"),
            "runtime": run.get("runtime"),
            "model_provider": run.get("model_provider"),
            "model": run.get("model"),
            "graph_steps": run.get("graph_steps") or [],
            "invocation_chain": run.get("invocation_chain") or [],
        },
        "agents_used": ["StudyAgent"],
        "skills_used": ["R-Tutor Skill"],
        "agent_runtime": "langgraph" if run.get("langgraph_enabled") else "state_machine_v1",
    }


def submit_study_agent_contribution(
    db: Session,
    *,
    human_entity_id: str,
    task_id: str,
    run: dict,
    agent_entity_id: str,
    skill_entity_id: str,
) -> ContributionEvent:
    """Turn StudyAgent output into a submitted Contribution Event."""
    from intelligence import capability_layer

    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    evidence = enrich_evidence(build_study_agent_evidence(run))
    capability_layer.precheck_submission(db, entity_id=human_entity_id, evidence=evidence)

    topic = run.get("topic") or "Study topic"
    draft = run.get("draft") or ""
    description = (
        f"Study notes produced via StudyAgent for: {topic}. "
        f"Invocation trace {run.get('trace_id')}."
    )

    contribution = ContributionEvent(
        task_id=task_id,
        primary_entity_id=human_entity_id,
        contribution_type="knowledge",
        description=description,
        evidence=evidence,
        status=ContributionStatus.submitted,
    )
    db.add(contribution)
    db.flush()

    participants = [
        (human_entity_id, ParticipantRole.creator, 0.40, {"action": "authored study notes from agent draft"}),
        (agent_entity_id, ParticipantRole.executor, 0.25, {"action": "StudyAgent graph execution"}),
        (skill_entity_id, ParticipantRole.skill_provider, 0.15, {"action": "R knowledge structuring"}),
    ]
    for entity_id, role, weight, p_evidence in participants:
        db.add(
            ContributionParticipant(
                contribution_id=contribution.id,
                entity_id=entity_id,
                role=role,
                weight=weight,
                evidence=p_evidence,
            )
        )

    trace = db.get(InvocationTrace, run.get("trace_id"))
    if trace:
        trace.contribution_id = contribution.id
        trace.task_id = task_id

    db.flush()
    return contribution


async def execute_study_agent(
    db: Session,
    *,
    human_entity_id: str,
    topic: str,
    task_id: str | None = None,
    agent_entity_id: str | None = None,
    skill_entity_id: str | None = None,
    llm_entity_id: str | None = None,
    llm_provider: str | None = None,
    contribution_id: str | None = None,
    submit_contribution: bool = False,
) -> dict:
    if submit_contribution and not task_id:
        raise HTTPException(status_code=400, detail="task_id is required when submit_contribution is true")

    human = db.get(Entity, human_entity_id)
    if not human or human.entity_type != EntityType.human:
        raise HTTPException(status_code=400, detail="Initiator must be a human entity")

    agent = db.get(Entity, agent_entity_id) if agent_entity_id else _entity_by_name(db, "StudyAgent", EntityType.agent)
    if not agent or agent.entity_type != EntityType.agent:
        raise HTTPException(status_code=404, detail="StudyAgent entity not found")

    skill_entity = (
        db.get(Entity, skill_entity_id)
        if skill_entity_id
        else _entity_by_name(db, "R-Tutor Skill", EntityType.skill)
    )
    if not skill_entity or skill_entity.entity_type != EntityType.skill:
        raise HTTPException(status_code=404, detail="Skill entity not found")

    llm_entity = db.get(Entity, llm_entity_id or LUMEN_0_ID)
    if not llm_entity or llm_entity.entity_type != EntityType.llm:
        raise HTTPException(status_code=404, detail="LLM witness entity not found")

    skill_row = db.query(Skill).filter(Skill.entity_id == skill_entity.id).first()
    skill_prompt = skill_row.prompt_template if skill_row else (skill_entity.description or "")

    provider = (llm_provider or os.getenv("STUDY_AGENT_LLM_PROVIDER", "mock")).lower()

    async def llm_invoke(prompt: str) -> tuple[str, str, str]:
        return await generate_ai_reply(prompt, provider=provider)

    graph_result = await run_study_agent_graph(
        topic=topic,
        skill_prompt=skill_prompt,
        llm_invoke=llm_invoke,
        model_provider=provider,
    )

    trace = InvocationTrace(
        initiator_id=human_entity_id,
        task_id=task_id,
        contribution_id=contribution_id,
        model_provider=graph_result.model_provider,
        status=InvocationStatus.completed,
    )
    db.add(trace)
    db.flush()

    chain = [
        (human_entity_id, agent.id, "uses"),
        (agent.id, skill_entity.id, "calls"),
        (skill_entity.id, llm_entity.id, "invokes_llm"),
    ]
    for order, (source_id, target_id, action) in enumerate(chain, start=1):
        db.add(
            InvocationStep(
                trace_id=trace.id,
                step_order=order,
                source_entity_id=source_id,
                target_entity_id=target_id,
                action=action,
            )
        )
    db.flush()

    trace_loaded = (
        db.query(InvocationTrace)
        .options(joinedload(InvocationTrace.steps))
        .filter(InvocationTrace.id == trace.id)
        .first()
    )

    result = {
        "trace_id": trace.id,
        "runtime": graph_result.runtime,
        "langgraph_enabled": graph_result.runtime == "langgraph",
        "model_provider": graph_result.model_provider,
        "model": graph_result.model,
        "topic": topic,
        "draft": graph_result.draft,
        "agent_entity_id": agent.id,
        "skill_entity_id": skill_entity.id,
        "llm_entity_id": llm_entity.id,
        "graph_steps": [
            {"node": s.node, "summary": s.summary, "detail": s.detail}
            for s in graph_result.steps
        ],
        "invocation_chain": [
            {
                "step_order": step.step_order,
                "source_entity_id": step.source_entity_id,
                "target_entity_id": step.target_entity_id,
                "action": step.action,
            }
            for step in sorted(trace_loaded.steps, key=lambda s: s.step_order)
        ],
        "advisory_only": True,
        "note": "Draft requires human review before contribution is approved.",
    }

    if submit_contribution:
        contribution = submit_study_agent_contribution(
            db,
            human_entity_id=human_entity_id,
            task_id=task_id,
            run=result,
            agent_entity_id=agent.id,
            skill_entity_id=skill_entity.id,
        )
        result["contribution"] = {
            "id": contribution.id,
            "status": contribution.status.value,
            "task_id": contribution.task_id,
            "evidence_hash": (contribution.evidence or {}).get("_pocp", {}).get("content_hash"),
        }
        result["note"] = "Contribution submitted; run auto-verify and human review to complete the loop."

    return result
