"""Agent Studio mission lifecycle."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from meta_agents_spec import NEXUS_ID
from models.agent_studio import AgentStudioMission, StudioMissionKind, StudioMissionStatus


def create_mission(
    db: Session,
    *,
    title: str,
    description: str | None = None,
    kind: str = "evolve",
    sponsor_entity_id: str | None = None,
    orchestrator_entity_id: str | None = None,
    goal_metrics: dict | None = None,
) -> AgentStudioMission:
    mission = AgentStudioMission(
        title=title.strip(),
        description=description,
        kind=StudioMissionKind(kind),
        status=StudioMissionStatus.draft,
        sponsor_entity_id=sponsor_entity_id,
        orchestrator_entity_id=orchestrator_entity_id or NEXUS_ID,
        goal_metrics=goal_metrics or {},
        metadata_={"studio_version": "1.0"},
    )
    db.add(mission)
    db.flush()
    return mission


def activate_mission(db: Session, mission_id: str) -> AgentStudioMission:
    mission = db.get(AgentStudioMission, mission_id)
    if mission is None:
        raise ValueError("Mission not found")
    mission.status = StudioMissionStatus.active
    mission.updated_at = datetime.utcnow()
    db.flush()
    return mission


def complete_mission(db: Session, mission_id: str) -> AgentStudioMission:
    mission = db.get(AgentStudioMission, mission_id)
    if mission is None:
        raise ValueError("Mission not found")
    mission.status = StudioMissionStatus.completed
    mission.completed_at = datetime.utcnow()
    mission.updated_at = datetime.utcnow()
    db.flush()
    return mission


def get_mission(db: Session, mission_id: str) -> AgentStudioMission | None:
    return db.get(AgentStudioMission, mission_id)


def list_missions(db: Session, *, limit: int = 50) -> list[AgentStudioMission]:
    return (
        db.query(AgentStudioMission)
        .order_by(AgentStudioMission.created_at.desc())
        .limit(limit)
        .all()
    )


def mission_to_dict(m: AgentStudioMission) -> dict:
    return {
        "id": m.id,
        "title": m.title,
        "description": m.description,
        "kind": m.kind.value,
        "status": m.status.value,
        "sponsor_entity_id": m.sponsor_entity_id,
        "orchestrator_entity_id": m.orchestrator_entity_id,
        "goal_metrics": m.goal_metrics or {},
        "metadata": m.metadata_ or {},
        "created_at": m.created_at.isoformat() if m.created_at else None,
        "completed_at": m.completed_at.isoformat() if m.completed_at else None,
    }
