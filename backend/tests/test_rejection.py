"""Unit tests for contribution rejection."""

import pytest
from unittest.mock import MagicMock
from uuid import uuid4

from models.contribution import (
    ContributionEvent,
    ContributionParticipant,
    ContributionStatus,
    ParticipantRole,
)
from models.entity import Entity, EntityType, EntityStatus
from services.rejection import reject_contribution


def make_entity(entity_type=EntityType.human, name="Test"):
    return Entity(
        id=str(uuid4()),
        entity_type=entity_type,
        name=name,
        status=EntityStatus.active,
    )


def make_contribution(primary_entity_id=None):
    pid = primary_entity_id or str(uuid4())
    return ContributionEvent(
        id=str(uuid4()),
        task_id=str(uuid4()),
        primary_entity_id=pid,
        contribution_type="knowledge",
        description="Test contribution",
        evidence={"url": "https://example.com"},
        status=ContributionStatus.submitted,
    )


class TestRejectContribution:
    """Tests for contribution rejection."""

    def test_sets_rejected_status(self):
        db = MagicMock()
        contribution = make_contribution()
        reviewer_id = str(uuid4())

        reject_contribution(db, contribution, reviewer_id, "Does not meet quality standards")

        assert contribution.status == ContributionStatus.rejected

    def test_creates_human_review(self):
        db = MagicMock()
        contribution = make_contribution()
        reviewer_id = str(uuid4())

        review = reject_contribution(db, contribution, reviewer_id, "Insufficient evidence")

        assert review.approved is False
        assert review.reviewer_id == reviewer_id
        assert "Insufficient evidence" in review.feedback

    def test_creates_ledger_record(self):
        db = MagicMock()
        contribution = make_contribution()
        reviewer_id = str(uuid4())

        reject_contribution(db, contribution, reviewer_id, "Off-topic content")

        # Check that a LedgerRecord was added
        ledger_calls = [call for call in db.add.call_args_list if "LedgerRecord" in str(call)]
        assert len(ledger_calls) >= 1

    def test_no_rewards_issued(self):
        """Rejection should not issue any CP or AI Credits."""
        db = MagicMock()
        human = make_entity(EntityType.human, "Alice")
        contribution = make_contribution(primary_entity_id=human.id)

        participant = ContributionParticipant(
            entity_id=human.id, role=ParticipantRole.creator, weight=1.0
        )
        contribution.participants = [participant]

        reviewer_id = str(uuid4())

        reject_contribution(db, contribution, reviewer_id, "Not approved")

        # Verify no CreditTransaction or wallet modifications were made
        for call in db.add.call_args_list:
            call_str = str(call)
            assert "CreditTransaction" not in call_str
            assert "Wallet" not in call_str
