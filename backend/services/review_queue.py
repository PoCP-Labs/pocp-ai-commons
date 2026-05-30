"""Human review queue for contributions awaiting final approval."""

from __future__ import annotations

from sqlalchemy.orm import Session, joinedload

from models.contribution import ContributionEvent, ContributionStatus
from models.entity import Entity
from services.reward_advisory import build_reward_advisory


def list_human_review_queue(db: Session, *, limit: int = 20) -> list[dict]:
    rows = (
        db.query(ContributionEvent)
        .options(joinedload(ContributionEvent.task), joinedload(ContributionEvent.participants))
        .filter(ContributionEvent.status == ContributionStatus.ai_verified)
        .order_by(ContributionEvent.created_at.asc())
        .limit(limit)
        .all()
    )

    entity_ids = {row.primary_entity_id for row in rows}
    for row in rows:
        entity_ids.update(p.entity_id for p in row.participants)
    entities = {
        entity.id: entity
        for entity in db.query(Entity).filter(Entity.id.in_(entity_ids)).all()
    } if entity_ids else {}

    queue: list[dict] = []
    for row in rows:
        advisory = build_reward_advisory(db, row)
        primary = entities.get(row.primary_entity_id)
        queue.append(
            {
                "contribution_id": row.id,
                "status": row.status.value,
                "description": row.description,
                "task_title": getattr(row.task, "title", None),
                "primary_entity": {
                    "id": row.primary_entity_id,
                    "name": primary.name if primary else None,
                },
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "recommended": advisory.get("recommended"),
                "consensus_passed": (advisory.get("consensus") or {}).get("passed"),
                "review_actions": ["approve", "reject", "request_changes"],
            }
        )
    return queue
