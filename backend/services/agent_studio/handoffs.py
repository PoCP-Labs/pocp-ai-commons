"""Handoff queue between Meta Agents."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from meta_agents_spec import META_AGENT_IDS, NEXUS_ID
from models.agent_studio import AgentStudioHandoff, StudioHandoffStatus


def _validate_agent(entity_id: str) -> None:
    if entity_id not in META_AGENT_IDS:
        raise ValueError(f"Unknown Meta Agent entity_id: {entity_id}")


def create_handoff(
    db: Session,
    *,
    from_agent_entity_id: str,
    to_agent_entity_id: str,
    mission_id: str | None = None,
    scope: str | None = None,
    files_touched: list[str] | None = None,
    tests_run: str | None = None,
    blockers: str | None = None,
) -> AgentStudioHandoff:
    _validate_agent(from_agent_entity_id)
    _validate_agent(to_agent_entity_id)
    handoff = AgentStudioHandoff(
        mission_id=mission_id,
        from_agent_entity_id=from_agent_entity_id,
        to_agent_entity_id=to_agent_entity_id,
        status=StudioHandoffStatus.pending,
        scope=scope,
        files_touched=files_touched or [],
        tests_run=tests_run,
        blockers=blockers,
    )
    db.add(handoff)
    db.flush()
    return handoff


def complete_handoff(
    db: Session,
    handoff_id: str,
    *,
    status: str = "completed",
    blockers: str | None = None,
) -> AgentStudioHandoff:
    handoff = db.get(AgentStudioHandoff, handoff_id)
    if handoff is None:
        raise ValueError("Handoff not found")
    handoff.status = StudioHandoffStatus(status)
    if blockers is not None:
        handoff.blockers = blockers
    if status in ("completed", "blocked"):
        handoff.completed_at = datetime.utcnow()
    db.flush()
    try:
        from services.agent_studio.auto_evolution import auto_evolution_enabled, ingest_handoff_memory

        if auto_evolution_enabled():
            ingest_handoff_memory(db, handoff)
    except Exception:
        pass
    return handoff


def list_handoffs(db: Session, *, mission_id: str | None = None, limit: int = 50) -> list[AgentStudioHandoff]:
    q = db.query(AgentStudioHandoff).order_by(AgentStudioHandoff.created_at.desc())
    if mission_id:
        q = q.filter(AgentStudioHandoff.mission_id == mission_id)
    return q.limit(limit).all()


def handoff_to_dict(h: AgentStudioHandoff) -> dict:
    return {
        "id": h.id,
        "mission_id": h.mission_id,
        "from_agent_entity_id": h.from_agent_entity_id,
        "to_agent_entity_id": h.to_agent_entity_id,
        "status": h.status.value,
        "scope": h.scope,
        "files_touched": h.files_touched or [],
        "tests_run": h.tests_run,
        "blockers": h.blockers,
        "created_at": h.created_at.isoformat() if h.created_at else None,
        "completed_at": h.completed_at.isoformat() if h.completed_at else None,
    }


def default_nexus_handoff_target() -> str:
    return NEXUS_ID
