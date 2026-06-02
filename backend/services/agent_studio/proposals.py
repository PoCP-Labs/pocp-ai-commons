"""Improvement proposals (Evaluate → Refine)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from models.agent_studio import AgentStudioProposal, StudioProposalStatus


def list_proposals(
    db: Session,
    *,
    agent_entity_id: str | None = None,
    status: str | None = None,
    limit: int = 50,
) -> list[AgentStudioProposal]:
    q = db.query(AgentStudioProposal).order_by(AgentStudioProposal.created_at.desc())
    if agent_entity_id:
        q = q.filter(AgentStudioProposal.agent_entity_id == agent_entity_id)
    if status:
        q = q.filter(AgentStudioProposal.status == StudioProposalStatus(status))
    return q.limit(limit).all()


def proposal_to_dict(p: AgentStudioProposal) -> dict:
    return {
        "id": p.id,
        "mission_id": p.mission_id,
        "agent_entity_id": p.agent_entity_id,
        "kind": p.kind.value,
        "status": p.status.value,
        "title": p.title,
        "rationale": p.rationale,
        "proposed_changes": p.proposed_changes or {},
        "reviewer_entity_id": p.reviewer_entity_id,
        "review_note": p.review_note,
        "source_outcome_ids": p.source_outcome_ids or [],
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "reviewed_at": p.reviewed_at.isoformat() if p.reviewed_at else None,
        "applied_at": p.applied_at.isoformat() if p.applied_at else None,
    }
