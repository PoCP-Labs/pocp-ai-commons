"""Record learning outcomes (Observe phase)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from meta_agents_spec import META_AGENT_IDS
from models.agent_studio import AgentStudioOutcome, StudioOutcomeKind, StudioOutcomeResult


def _parse_result(value: str) -> StudioOutcomeResult:
    if value == "pass":
        return StudioOutcomeResult.pass_
    return StudioOutcomeResult(value)


def record_outcome(
    db: Session,
    *,
    agent_entity_id: str,
    kind: str,
    result: str,
    mission_id: str | None = None,
    handoff_id: str | None = None,
    score: float | None = None,
    summary: str | None = None,
    evidence: dict | None = None,
) -> AgentStudioOutcome:
    if agent_entity_id not in META_AGENT_IDS:
        raise ValueError(f"Unknown Meta Agent entity_id: {agent_entity_id}")
    outcome = AgentStudioOutcome(
        mission_id=mission_id,
        handoff_id=handoff_id,
        agent_entity_id=agent_entity_id,
        kind=StudioOutcomeKind(kind),
        result=_parse_result(result),
        score=score,
        summary=summary,
        evidence=evidence or {},
    )
    db.add(outcome)
    db.flush()
    try:
        from services.agent_studio.auto_evolution import auto_evolution_enabled, ingest_outcome_memory

        if auto_evolution_enabled():
            ingest_outcome_memory(db, outcome)
            meta = dict(outcome.metadata_ or {})
            meta["memory_ingested"] = True
            outcome.metadata_ = meta
            db.flush()
    except Exception:
        pass
    return outcome


def outcome_to_dict(o: AgentStudioOutcome) -> dict:
    return {
        "id": o.id,
        "mission_id": o.mission_id,
        "handoff_id": o.handoff_id,
        "agent_entity_id": o.agent_entity_id,
        "kind": o.kind.value,
        "result": o.result.value,
        "score": o.score,
        "summary": o.summary,
        "evidence": o.evidence or {},
        "created_at": o.created_at.isoformat() if o.created_at else None,
    }
