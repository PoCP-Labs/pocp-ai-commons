"""Reject contribution — moves to rejected status with audit trail."""

from sqlalchemy.orm import Session

from models.contribution import (
    ContributionEvent,
    ContributionStatus,
    HumanReview,
)
from models.entity import EntityType
from models.ledger import LedgerRecord


def reject_contribution(
    db: Session,
    contribution: ContributionEvent,
    reviewer_id: str,
    feedback: str,
) -> HumanReview:
    """Human reviewer rejects a contribution.

    Rejected contributions:
    - Move to 'rejected' status (terminal)
    - No CP or AI Credits are issued
    - Are recorded in the ledger for audit
    - Can be re-submitted as a new contribution event
    """
    review = HumanReview(
        contribution_id=contribution.id,
        reviewer_id=reviewer_id,
        approved=False,
        feedback=feedback,
    )
    db.add(review)
    contribution.status = ContributionStatus.rejected

    db.add(
        LedgerRecord(
            contribution_id=contribution.id,
            event_type="contribution_rejected",
            payload={
                "contribution_id": contribution.id,
                "reviewer_id": reviewer_id,
                "feedback": feedback,
                "participants": [
                    {
                        "entity_id": p.entity_id,
                        "role": p.role.value,
                        "weight": p.weight,
                    }
                    for p in contribution.participants
                ],
            },
        )
    )

    db.flush()
    return review
