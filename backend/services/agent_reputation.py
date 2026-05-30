"""Off-chain agent reputation (ERC-8004 Reputation Registry pattern)."""

from sqlalchemy.orm import Session

from models.agent_feedback import AgentFeedback
from models.entity import Entity, EntityType


class AgentReputationError(ValueError):
    pass


def give_agent_feedback(
    db: Session,
    *,
    agent_entity_id: str,
    reviewer_entity_id: str,
    score: float,
    comment: str | None = None,
    contribution_id: str | None = None,
    tag1: str | None = None,
    tag2: str | None = None,
) -> AgentFeedback:
    agent = db.query(Entity).filter(Entity.id == agent_entity_id).first()
    if not agent or agent.entity_type != EntityType.agent:
        raise AgentReputationError("Target must be an agent entity")

    reviewer = db.query(Entity).filter(Entity.id == reviewer_entity_id).first()
    if not reviewer:
        raise AgentReputationError("Reviewer entity not found")
    if reviewer_entity_id == agent_entity_id:
        raise AgentReputationError("Self-feedback is not allowed (ERC-8004 guardrail)")

    normalized_score = max(0.0, min(float(score), 100.0))
    value_dec = round(normalized_score, 2)

    existing = (
        db.query(AgentFeedback)
        .filter(
            AgentFeedback.agent_entity_id == agent_entity_id,
            AgentFeedback.reviewer_entity_id == reviewer_entity_id,
            AgentFeedback.contribution_id == contribution_id,
        )
        .first()
    )
    if existing:
        existing.score = normalized_score
        existing.value_dec = value_dec
        existing.comment = comment
        existing.tag1 = tag1
        existing.tag2 = tag2
        db.flush()
        return existing

    feedback = AgentFeedback(
        agent_entity_id=agent_entity_id,
        reviewer_entity_id=reviewer_entity_id,
        contribution_id=contribution_id,
        score=normalized_score,
        value_dec=value_dec,
        comment=comment,
        tag1=tag1,
        tag2=tag2,
    )
    db.add(feedback)
    db.flush()
    return feedback


def get_agent_reputation_summary(db: Session, agent_entity_id: str) -> dict:
    agent = db.query(Entity).filter(Entity.id == agent_entity_id).first()
    if not agent:
        raise AgentReputationError("Agent entity not found")

    rows = (
        db.query(AgentFeedback)
        .filter(AgentFeedback.agent_entity_id == agent_entity_id)
        .order_by(AgentFeedback.created_at.desc())
        .all()
    )
    if not rows:
        return {
            "agent_entity_id": agent_entity_id,
            "agent_name": agent.name,
            "feedback_count": 0,
            "average_score": 0.0,
            "average_value_dec": 0.0,
            "unique_reviewers": 0,
            "recent_feedback": [],
            "registry_compat": "erc-8004-offchain-v0",
        }

    avg_score = sum(r.score for r in rows) / len(rows)
    reviewers = {r.reviewer_entity_id for r in rows}
    return {
        "agent_entity_id": agent_entity_id,
        "agent_name": agent.name,
        "feedback_count": len(rows),
        "average_score": round(avg_score, 2),
        "average_value_dec": round(sum(r.value_dec for r in rows) / len(rows), 2),
        "unique_reviewers": len(reviewers),
        "recent_feedback": [
            {
                "id": row.id,
                "reviewer_entity_id": row.reviewer_entity_id,
                "contribution_id": row.contribution_id,
                "score": row.score,
                "value_dec": row.value_dec,
                "comment": row.comment,
                "tag1": row.tag1,
                "tag2": row.tag2,
                "created_at": row.created_at.isoformat(),
            }
            for row in rows[:10]
        ],
        "registry_compat": "erc-8004-offchain-v0",
    }


def list_agent_clients(db: Session, agent_entity_id: str) -> list[str]:
    rows = (
        db.query(AgentFeedback.reviewer_entity_id)
        .filter(AgentFeedback.agent_entity_id == agent_entity_id)
        .distinct()
        .all()
    )
    return [row[0] for row in rows]
