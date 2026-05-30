"""Governance assistant — advisory network health and policy summaries."""

from __future__ import annotations

import os
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from models.contribution import ContributionEvent, ContributionStatus
from models.entity import Entity
from models.ledger import LedgerRecord
from services.finalization import is_auto_finalization_enabled


def run_governance_summary(db: Session) -> dict[str, Any]:
    """Advisory governance packet. Does not change policy or approve contributions."""
    entity_counts: dict[str, int] = {}
    for row in db.query(Entity.entity_type, func.count(Entity.id)).group_by(Entity.entity_type).all():
        entity_counts[row[0].value if hasattr(row[0], "value") else str(row[0])] = row[1]

    pending_finalize = (
        db.query(func.count(ContributionEvent.id))
        .filter(ContributionEvent.status == ContributionStatus.ai_verified)
        .scalar()
        or 0
    )
    in_verification = (
        db.query(func.count(ContributionEvent.id))
        .filter(ContributionEvent.status == ContributionStatus.submitted)
        .scalar()
        or 0
    )
    approved = (
        db.query(func.count(ContributionEvent.id))
        .filter(ContributionEvent.status == ContributionStatus.approved)
        .scalar()
        or 0
    )
    ledger_height = db.query(func.count(LedgerRecord.id)).scalar() or 0

    observations: list[str] = []
    if pending_finalize > 0 and not is_auto_finalization_enabled():
        observations.append(f"{pending_finalize} contribution(s) await policy finalization.")
    elif pending_finalize > 0:
        observations.append(
            f"{pending_finalize} contribution(s) ai_verified — auto-finalize should clear under entity_equal policy."
        )
    if in_verification > 0:
        observations.append(f"{in_verification} contribution(s) in submitted state — run witness verify.")
    if entity_counts.get("skill", 0) == 0:
        observations.append("No Skill entities registered — matching engine has limited capability coverage.")
    if not os.getenv("OPENAI_API_KEY") and not os.getenv("DEEPSEEK_API_KEY"):
        observations.append("No external verifier API keys — network runs on mock AI witness fallback.")

    return {
        "advisory_only": True,
        "entity_equal_automation": is_auto_finalization_enabled(),
        "network_snapshot": {
            "entities_by_type": entity_counts,
            "contributions_approved": approved,
            "contributions_pending_finalization": pending_finalize,
            "contributions_pending_human_review": pending_finalize,
            "contributions_submitted": in_verification,
            "ledger_blocks": ledger_height,
        },
        "policy_parameters": {
            "daily_contribution_limit": int(os.getenv("DAILY_CONTRIBUTION_LIMIT", "10")),
            "daily_ai_credits_burn_limit": float(os.getenv("DAILY_AI_CREDITS_BURN_LIMIT", "200")),
            "ai_chat_cost_per_message": float(os.getenv("AI_CHAT_COST_PER_MESSAGE", "5")),
            "starter_ai_credits": float(os.getenv("STARTER_AI_CREDITS", "100")),
        },
        "observations": observations,
        "principle": "Governance follows verifiable contribution — Entity-equal, policy-automated, auditable.",
    }
