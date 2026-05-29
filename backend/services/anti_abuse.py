import os
from datetime import datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from models.ai_usage import AIUsageLog
from models.contribution import ContributionEvent

DAILY_CONTRIBUTION_LIMIT = int(os.getenv("DAILY_CONTRIBUTION_LIMIT", "10"))
DAILY_AI_CREDITS_BURN_LIMIT = float(os.getenv("DAILY_AI_CREDITS_BURN_LIMIT", "200"))


def _day_start() -> datetime:
    now = datetime.utcnow()
    return datetime(now.year, now.month, now.day)


def require_evidence(evidence: dict | None) -> None:
    if not evidence or not any(v for v in evidence.values()):
        raise HTTPException(status_code=400, detail="Evidence is required for contribution submission")


def check_daily_contribution_limit(db: Session, entity_id: str) -> None:
    count = (
        db.query(func.count(ContributionEvent.id))
        .filter(
            ContributionEvent.primary_entity_id == entity_id,
            ContributionEvent.created_at >= _day_start(),
        )
        .scalar()
        or 0
    )
    if count >= DAILY_CONTRIBUTION_LIMIT:
        raise HTTPException(
            status_code=429,
            detail=f"Daily contribution limit reached: {DAILY_CONTRIBUTION_LIMIT}",
        )


def check_daily_ai_burn_limit(db: Session, entity_id: str, next_cost: float) -> None:
    burned = (
        db.query(func.coalesce(func.sum(AIUsageLog.credits_spent), 0.0))
        .filter(
            AIUsageLog.entity_id == entity_id,
            AIUsageLog.created_at >= _day_start(),
        )
        .scalar()
        or 0.0
    )
    if float(burned) + next_cost > DAILY_AI_CREDITS_BURN_LIMIT:
        raise HTTPException(
            status_code=429,
            detail=f"Daily AI Credits burn limit reached: {DAILY_AI_CREDITS_BURN_LIMIT}",
        )
