"""Contribution approval and reward distribution."""

from sqlalchemy.orm import Session

from config import (
    AI_VERIFIER_MODEL,
    AI_VERIFIER_THRESHOLD,
    DEFAULT_REWARD_AI_CREDITS,
    DEFAULT_REWARD_CP,
    REGISTRATION_AI_CREDITS,
)
from models.contribution import (
    AiVerifierResult,
    ContributionEvent,
    ContributionStatus,
    HumanReview,
    ParticipantRole,
)
from models.entity import Entity, EntityType
from models.ledger import LedgerRecord
from models.wallet import CreditTransaction, CreditType, ReputationScore, Wallet


def _get_or_create_wallet(db: Session, entity_id: str) -> Wallet:
    wallet = db.query(Wallet).filter(Wallet.entity_id == entity_id).first()
    if wallet is None:
        wallet = Wallet(entity_id=entity_id)
        db.add(wallet)
        db.flush()
    return wallet


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
    model_provider: str = AI_VERIFIER_MODEL,
    score: float = 0.85,
    feedback: str = "Content is well-structured and accurate.",
    details: dict | None = None,
) -> AiVerifierResult:
    """Record AI advisory verification result.

    This can be called with:
    - A pre-computed score/feedback (from the real AI verifier)
    - Or with a manual score (for dev/testing)

    AI verification is ADVISORY ONLY. It never sets 'approved' status.
    """
    passed = score >= AI_VERIFIER_THRESHOLD
    result = AiVerifierResult(
        contribution_id=contribution.id,
        model_provider=model_provider,
        score=score,
        feedback=feedback,
        passed=passed,
    )
    db.add(result)
    contribution.status = (
        ContributionStatus.ai_verified if passed else ContributionStatus.rejected
    )
    db.flush()
    return result


def grant_registration_credits(db: Session, entity: Entity) -> Wallet | None:
    """Issue starter AI Credits to newly registered human entities."""
    if entity.entity_type != EntityType.human:
        return None

    wallet = _get_or_create_wallet(db, entity.id)
    if wallet.ai_credits > 0 or wallet.cp_balance > 0:
        return wallet

    starter_credits = float(REGISTRATION_AI_CREDITS)
    wallet.ai_credits = starter_credits
    db.add(
        CreditTransaction(
            wallet_id=wallet.id,
            amount=starter_credits,
            credit_type=CreditType.ai_credits,
            reason="Registration grant",
        )
    )
    db.add(
        LedgerRecord(
            contribution_id=None,
            event_type="registration_grant",
            payload={
                "entity_id": entity.id,
                "ai_credits": starter_credits,
            },
        )
    )
    db.flush()
    return wallet


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

    for participant in contribution.participants:
        entity = db.query(Entity).filter(Entity.id == participant.entity_id).first()
        if entity is None:
            continue

        if entity.entity_type == EntityType.human and participant.role in (
            ParticipantRole.creator,
            ParticipantRole.executor,
        ):
            wallet = _get_or_create_wallet(db, entity.id)
            weight = participant.weight or 0.4  # default weight if not set
            cp_amount = round(DEFAULT_REWARD_CP * weight / 0.4, 2)
            ai_amount = round(DEFAULT_REWARD_AI_CREDITS * weight / 0.4, 2)

            wallet.cp_balance += cp_amount
            wallet.ai_credits += ai_amount

            db.add(
                CreditTransaction(
                    wallet_id=wallet.id,
                    contribution_id=contribution.id,
                    amount=cp_amount,
                    credit_type=CreditType.cp,
                    reason=f"Contribution reward ({participant.role.value})",
                )
            )
            db.add(
                CreditTransaction(
                    wallet_id=wallet.id,
                    contribution_id=contribution.id,
                    amount=ai_amount,
                    credit_type=CreditType.ai_credits,
                    reason=f"Contribution reward ({participant.role.value})",
                )
            )
            rewards["credits"].append(
                {"entity_id": entity.id, "name": entity.name, "cp": cp_amount, "ai_credits": ai_amount}
            )

        elif entity.entity_type == EntityType.skill:
            weight = participant.weight or 0.15
            rep_amount = round(5 * weight / 0.15, 2)
            _add_reputation(db, entity.id, rep_amount, "skill")
            rewards["reputation"].append(
                {"entity_id": entity.id, "name": entity.name, "category": "skill", "amount": rep_amount}
            )

        elif entity.entity_type == EntityType.agent:
            weight = participant.weight or 0.25
            rep_amount = round(3 * weight / 0.25, 2)
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
    db.add(
        LedgerRecord(
            contribution_id=contribution.id,
            event_type="contribution_approved",
            payload=ledger_payload,
        )
    )
    db.flush()
    return rewards
