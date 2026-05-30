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
from services.reputation_audit import record_reputation_audit
from services.rights import issue_contribution_rights, issue_entity_bc_grant, issue_registration_bc
from services.rights_conversion import reputation_amount_for_participant
from services.webhook_dispatcher import dispatch_review_event


def _add_reputation(
    db: Session,
    entity_id: str,
    amount: float,
    category: str,
    *,
    source: str = "contribution_approval",
    reason: str | None = None,
    reference_id: str | None = None,
    actor_entity_id: str | None = None,
) -> ReputationScore:
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
    db.flush()
    record_reputation_audit(
        db,
        entity_id=entity_id,
        category=category,
        delta=amount,
        balance_after=rep.score,
        source=source,
        reason=reason,
        reference_id=reference_id,
        actor_entity_id=actor_entity_id,
    )
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
    feedback: str = "Approved (traceable finalization).",
    *,
    finalization: dict | None = None,
) -> dict:
    """Final approval → credits for humans, reputation for agents/skills → ledger.

    Any Entity type may finalize when instance policy allows (entity-equal protocol).
    """
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
            rep_amount = reputation_amount_for_participant(entity, participant)
            if rep_amount is None:
                rep_amount = skill_rep_base
            _add_reputation(
                db,
                entity.id,
                rep_amount,
                "skill",
                source="contribution_approval",
                reason="Approved contribution participant reward",
                reference_id=contribution.id,
                actor_entity_id=reviewer_id,
            )
            rewards["reputation"].append(
                {"entity_id": entity.id, "name": entity.name, "category": "skill", "amount": rep_amount}
            )
            bc_grant = issue_entity_bc_grant(
                db, contribution=contribution, participant=participant, entity=entity
            )
            if bc_grant:
                rewards["credits"].append(
                    {
                        "entity_id": entity.id,
                        "name": entity.name,
                        "cp": 0,
                        "ai_credits": bc_grant.amount,
                        "entity_type": "skill",
                    }
                )

        elif entity.entity_type == EntityType.agent:
            rep_amount = reputation_amount_for_participant(entity, participant)
            if rep_amount is None:
                rep_amount = agent_rep_base
            _add_reputation(
                db,
                entity.id,
                rep_amount,
                "agent",
                source="contribution_approval",
                reason="Approved contribution participant reward",
                reference_id=contribution.id,
                actor_entity_id=reviewer_id,
            )
            rewards["reputation"].append(
                {"entity_id": entity.id, "name": entity.name, "category": "agent", "amount": rep_amount}
            )
            bc_grant = issue_entity_bc_grant(
                db, contribution=contribution, participant=participant, entity=entity
            )
            if bc_grant:
                rewards["credits"].append(
                    {
                        "entity_id": entity.id,
                        "name": entity.name,
                        "cp": 0,
                        "ai_credits": bc_grant.amount,
                        "entity_type": "agent",
                    }
                )

        elif entity.entity_type == EntityType.llm:
            rep_amount = reputation_amount_for_participant(entity, participant)
            if rep_amount is None:
                rep_amount = float(
                    get_rewards_config()["contribution_defaults"].get("llm", {}).get("reputation_base", 2)
                )
            _add_reputation(
                db,
                entity.id,
                rep_amount,
                "llm",
                source="contribution_approval",
                reason="Approved contribution participant reward",
                reference_id=contribution.id,
                actor_entity_id=reviewer_id,
            )
            rewards["reputation"].append(
                {"entity_id": entity.id, "name": entity.name, "category": "llm", "amount": rep_amount}
            )
            bc_grant = issue_entity_bc_grant(
                db, contribution=contribution, participant=participant, entity=entity
            )
            if bc_grant:
                rewards["credits"].append(
                    {
                        "entity_id": entity.id,
                        "name": entity.name,
                        "cp": 0,
                        "ai_credits": bc_grant.amount,
                        "entity_type": "llm",
                    }
                )

    ledger_payload = {
        "contribution_id": contribution.id,
        "status": contribution.status.value,
        "rewards": rewards,
        "finalization": finalization
        or {
            "mode": "manual",
            "applied": True,
            "finalizer_entity_id": reviewer_id,
            "policy_id": None,
            "policy_version": None,
        },
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
    dispatch_review_event(
        "contribution.approved",
        {
            "contribution_id": contribution.id,
            "reviewer_id": reviewer_id,
            "rewards": rewards,
            "finalization": ledger_payload.get("finalization"),
        },
    )
    db.flush()
    return rewards


def reject_contribution(
    db: Session,
    contribution: ContributionEvent,
    reviewer_id: str,
    feedback: str = "Rejected (traceable finalization).",
) -> HumanReview:
    """Entity finalization rejection — any allowed Entity type may reject under policy."""
    review = HumanReview(
        contribution_id=contribution.id,
        reviewer_id=reviewer_id,
        approved=False,
        feedback=feedback,
    )
    db.add(review)
    contribution.status = ContributionStatus.rejected

    append_ledger_record(
        db,
        contribution_id=contribution.id,
        event_type="contribution_rejected",
        payload={
            "contribution_id": contribution.id,
            "status": contribution.status.value,
            "reviewer_id": reviewer_id,
            "feedback": feedback,
        },
    )
    dispatch_review_event(
        "contribution.rejected",
        {
            "contribution_id": contribution.id,
            "reviewer_id": reviewer_id,
            "feedback": feedback,
        },
    )
    db.flush()
    return review


def request_contribution_changes(
    db: Session,
    contribution: ContributionEvent,
    reviewer_id: str,
    feedback: str = "Please revise and resubmit.",
) -> HumanReview:
    """Request revision without full rejection — any Entity finalizer may invoke."""
    if contribution.status != ContributionStatus.ai_verified:
        raise ValueError("Request changes is only available after AI verification")

    review = HumanReview(
        contribution_id=contribution.id,
        reviewer_id=reviewer_id,
        approved=False,
        feedback=f"[request_changes] {feedback}",
    )
    db.add(review)
    contribution.status = ContributionStatus.submitted

    append_ledger_record(
        db,
        contribution_id=contribution.id,
        event_type="contribution_request_changes",
        payload={
            "contribution_id": contribution.id,
            "status": contribution.status.value,
            "reviewer_id": reviewer_id,
            "feedback": feedback,
        },
    )
    dispatch_review_event(
        "contribution.request_changes",
        {
            "contribution_id": contribution.id,
            "reviewer_id": reviewer_id,
            "feedback": feedback,
        },
    )
    db.flush()
    return review
