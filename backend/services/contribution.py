"""Contribution approval and reward distribution."""

import json

from sqlalchemy.orm import Session

from models.contribution import (
    AiVerifierResult,
    ContributionEvent,
    ContributionStatus,
    HumanReview,
    ParticipantRole,
)
from models.entity import Entity, EntityType
from models.wallet import ReputationScore, Wallet
from services.ledger_chain import append_ledger_record
from services.protocol_config import get_rewards_config
from services.rights import issue_contribution_rights, issue_registration_bc


def _add_reputation(db: Session, entity_id: str, amount: float, category: str) -> ReputationScore:
    rep = (
        db.query(ReputationScore)
        .filter(ReputationScore.entity_id == entity_id, ReputationScore.category == category)
        .first()
    )
    if rep is None:
        rep = ReputationScore(entity_id=entity_id, score=amount, category=category)
        db.add(rep)
    else:
        rep.score += amount
    return rep


def run_ai_verification(
    db: Session,
    contribution: ContributionEvent,
    model_provider: str = "deepseek",
    score: float = 0.85,
    feedback: str = "Content is well-structured and accurate.",
    required_passing_count: int = 1,
    details: dict | None = None,
) -> AiVerifierResult:
    passed = score >= 0.7
    stored_feedback = feedback
    if details is not None:
        stored_feedback = json.dumps({"feedback": feedback, "details": details}, ensure_ascii=False)
    result = AiVerifierResult(
        contribution_id=contribution.id,
        model_provider=model_provider,
        score=score,
        feedback=stored_feedback,
        passed=passed,
    )
    db.add(result)
    db.flush()

    results = (
        db.query(AiVerifierResult)
        .filter(AiVerifierResult.contribution_id == contribution.id)
        .all()
    )
    passing = [r for r in results if r.passed and r.score >= 0.7]

    if not passing and any(not r.passed or r.score < 0.7 for r in results):
        contribution.status = ContributionStatus.rejected
    elif len(passing) >= required_passing_count:
        contribution.status = ContributionStatus.ai_verified
    elif passing:
        contribution.status = ContributionStatus.submitted
    else:
        contribution.status = ContributionStatus.rejected

    db.flush()
    return result


def grant_registration_credits(db: Session, entity: Entity) -> Wallet | None:
    """Issue starter AI Credits to newly registered human entities."""
    return issue_registration_bc(db, entity)


def approve_contribution(
    db: Session,
    contribution: ContributionEvent,
    reviewer_id: str,
    feedback: str = "Approved by human reviewer.",
) -> dict:
    """Human review → credits for humans, reputation for agents/skills → ledger."""
    if reviewer_id == contribution.primary_entity_id:
        raise ValueError("Reviewer cannot approve their own contribution")

    review = HumanReview(
        contribution_id=contribution.id,
        reviewer_id=reviewer_id,
        approved=True,
        feedback=feedback,
    )
    db.add(review)
    contribution.status = ContributionStatus.approved

    rewards: dict = {"credits": [], "reputation": []}
    defaults = get_rewards_config()["contribution_defaults"]
    skill_rep_base = float(defaults["skill"]["reputation_base"])
    agent_rep_base = float(defaults["agent"]["reputation_base"])

    for participant in contribution.participants:
        entity = db.query(Entity).filter(Entity.id == participant.entity_id).first()
        if entity is None:
            continue

        if entity.entity_type == EntityType.human and participant.role in (
            ParticipantRole.creator,
            ParticipantRole.executor,
        ):
            grants = issue_contribution_rights(
                db,
                contribution=contribution,
                participant=participant,
                entity=entity,
            )
            cp_amount = sum(grant.amount for grant in grants if grant.kind == "cp")
            ai_amount = sum(grant.amount for grant in grants if grant.kind == "bc")
            rewards["credits"].append(
                {
                    "entity_id": entity.id,
                    "name": entity.name,
                    "cp": cp_amount,
                    "ai_credits": ai_amount,
                    "rights": [
                        {
                            "kind": grant.kind,
                            "version": grant.version,
                            "amount": grant.amount,
                            "spendable": grant.spendable,
                            "transferable": grant.transferable,
                        }
                        for grant in grants
                    ],
                }
            )

        elif entity.entity_type == EntityType.skill:
            rep_amount = round(skill_rep_base * participant.weight / 0.15, 2) if participant.weight else skill_rep_base
            _add_reputation(db, entity.id, rep_amount, "skill")
            rewards["reputation"].append(
                {"entity_id": entity.id, "name": entity.name, "category": "skill", "amount": rep_amount}
            )

        elif entity.entity_type == EntityType.agent:
            rep_amount = round(agent_rep_base * participant.weight / 0.25, 2) if participant.weight else agent_rep_base
            _add_reputation(db, entity.id, rep_amount, "agent")
            rewards["reputation"].append(
                {"entity_id": entity.id, "name": entity.name, "category": "agent", "amount": rep_amount}
            )

    ledger_payload = {
        "contribution_id": contribution.id,
        "status": contribution.status.value,
        "rewards": rewards,
        "participants": [
            {
                "entity_id": p.entity_id,
                "role": p.role.value,
                "weight": p.weight,
            }
            for p in contribution.participants
        ],
    }
    append_ledger_record(
        db,
        contribution_id=contribution.id,
        event_type="contribution_approved",
        payload=ledger_payload,
    )
    db.flush()
    return rewards
