"""Tests for Contribution Event protocol properties and constraints.

These tests verify the protocol rules defined in PROTOCOL-SPEC-v0.2.md §2.4.
"""

from uuid import uuid4

from models.contribution import (
    AiVerifierResult,
    ContributionEvent,
    ContributionParticipant,
    ContributionStatus,
    HumanReview,
    ParticipantRole,
)


def make_contribution(**overrides):
    defaults = {
        "id": str(uuid4()),
        "task_id": str(uuid4()),
        "primary_entity_id": str(uuid4()),
        "contribution_type": "knowledge",
        "description": "Test contribution claim",
        "evidence": {"url": "https://example.com", "content_hash": "sha256:abc"},
        "status": ContributionStatus.submitted,
    }
    defaults.update(overrides)
    return ContributionEvent(**defaults)


class TestEvidencePrinciple:
    """Principle 4: Evidence Bundle — no evidence, no Contribution Event."""

    def test_has_evidence_true(self):
        contrib = make_contribution(evidence={"url": "https://example.com"})
        assert contrib.has_evidence is True

    def test_has_evidence_empty_dict_false(self):
        contrib = make_contribution(evidence={})
        assert contrib.has_evidence is False

    def test_has_evidence_none_false(self):
        contrib = make_contribution(evidence=None)
        assert contrib.has_evidence is False


class TestParticipantPrinciple:
    """Must have at least one attributed participant."""

    def test_has_participants_true(self):
        contrib = make_contribution()
        contrib.participants = [
            ContributionParticipant(
                entity_id=str(uuid4()), role=ParticipantRole.creator, weight=1.0
            )
        ]
        assert contrib.has_participants is True

    def test_has_participants_false(self):
        contrib = make_contribution()
        contrib.participants = []
        assert contrib.has_participants is False


class TestAIVerificationPrinciple:
    """Principle 5: Verification Required — AI may advise, must not adjudicate."""

    def test_has_ai_verification_true(self):
        contrib = make_contribution()
        contrib.ai_verifications = [
            AiVerifierResult(
                contribution_id=contrib.id,
                model_provider="deepseek",
                score=0.85,
                feedback="Good",
                passed=True,
            )
        ]
        assert contrib.has_ai_verification is True

    def test_has_ai_verification_false(self):
        contrib = make_contribution()
        contrib.ai_verifications = []
        assert contrib.has_ai_verification is False


class TestHumanApprovalPrinciple:
    """Principle 6: Accountability — human final review required."""

    def test_has_human_approval_true(self):
        contrib = make_contribution()
        contrib.human_reviews = [
            HumanReview(
                contribution_id=contrib.id,
                reviewer_id=str(uuid4()),
                approved=True,
                feedback="Approved",
            )
        ]
        assert contrib.has_human_approval is True

    def test_has_human_approval_false(self):
        contrib = make_contribution()
        contrib.human_reviews = []
        assert contrib.has_human_approval is False

    def test_has_human_approval_mixed(self):
        contrib = make_contribution()
        contrib.human_reviews = [
            HumanReview(
                contribution_id=contrib.id,
                reviewer_id=str(uuid4()),
                approved=False,
                feedback="Rejected",
            ),
            HumanReview(
                contribution_id=contrib.id,
                reviewer_id=str(uuid4()),
                approved=True,
                feedback="Approved on second review",
            ),
        ]
        assert contrib.has_human_approval is True


class TestEstablishedProperty:
    """§2.4.4: When a Contribution Event is Formally Established."""

    def _full_contribution(self, status=ContributionStatus.approved):
        contrib = make_contribution(status=status)
        contrib.participants = [
            ContributionParticipant(
                entity_id=str(uuid4()), role=ParticipantRole.creator, weight=1.0
            )
        ]
        contrib.ai_verifications = [
            AiVerifierResult(
                contribution_id=contrib.id,
                model_provider="deepseek",
                score=0.85,
                feedback="Good",
                passed=True,
            )
        ]
        contrib.human_reviews = [
            HumanReview(
                contribution_id=contrib.id,
                reviewer_id=str(uuid4()),
                approved=True,
                feedback="Approved",
            )
        ]
        return contrib

    def test_established_when_all_conditions_met(self):
        contrib = self._full_contribution(ContributionStatus.approved)
        assert contrib.is_established is True

    def test_not_established_draft(self):
        contrib = self._full_contribution(ContributionStatus.draft)
        assert contrib.is_established is False

    def test_not_established_submitted(self):
        contrib = self._full_contribution(ContributionStatus.submitted)
        assert contrib.is_established is False

    def test_not_established_ai_verified(self):
        contrib = self._full_contribution(ContributionStatus.ai_verified)
        assert contrib.is_established is False

    def test_not_established_rejected(self):
        contrib = self._full_contribution(ContributionStatus.rejected)
        assert contrib.is_established is False

    def test_not_established_no_evidence(self):
        contrib = self._full_contribution(ContributionStatus.approved)
        contrib.evidence = {}
        assert contrib.is_established is False

    def test_not_established_no_participants(self):
        contrib = self._full_contribution(ContributionStatus.approved)
        contrib.participants = []
        assert contrib.is_established is False

    def test_not_established_no_ai_verification(self):
        contrib = self._full_contribution(ContributionStatus.approved)
        contrib.ai_verifications = []
        assert contrib.is_established is False

    def test_not_established_no_human_approval(self):
        contrib = self._full_contribution(ContributionStatus.approved)
        contrib.human_reviews = []
        assert contrib.is_established is False


class TestValidateForSubmission:
    """Validate that a contribution can be submitted."""

    def test_valid_contribution_no_errors(self):
        contrib = make_contribution()
        contrib.participants = [
            ContributionParticipant(
                entity_id=str(uuid4()), role=ParticipantRole.creator, weight=1.0
            )
        ]
        errors = contrib.validate_for_submission()
        assert errors == []

    def test_missing_task_id(self):
        contrib = make_contribution(task_id=None)
        contrib.participants = [
            ContributionParticipant(
                entity_id=str(uuid4()), role=ParticipantRole.creator, weight=1.0
            )
        ]
        errors = contrib.validate_for_submission()
        assert len(errors) >= 1
        assert any("task" in e.lower() for e in errors)

    def test_missing_primary_entity(self):
        contrib = make_contribution(primary_entity_id=None)
        contrib.participants = [
            ContributionParticipant(
                entity_id=str(uuid4()), role=ParticipantRole.creator, weight=1.0
            )
        ]
        errors = contrib.validate_for_submission()
        assert len(errors) >= 1
        assert any("primary" in e.lower() or "responsible" in e.lower() for e in errors)

    def test_missing_description(self):
        contrib = make_contribution(description=None)
        contrib.participants = [
            ContributionParticipant(
                entity_id=str(uuid4()), role=ParticipantRole.creator, weight=1.0
            )
        ]
        errors = contrib.validate_for_submission()
        assert len(errors) >= 1
        assert any("description" in e.lower() or "claim" in e.lower() for e in errors)

    def test_missing_evidence(self):
        contrib = make_contribution(evidence={})
        contrib.participants = [
            ContributionParticipant(
                entity_id=str(uuid4()), role=ParticipantRole.creator, weight=1.0
            )
        ]
        errors = contrib.validate_for_submission()
        assert len(errors) >= 1
        assert any("evidence" in e.lower() for e in errors)

    def test_missing_participants(self):
        contrib = make_contribution()
        contrib.participants = []
        errors = contrib.validate_for_submission()
        assert len(errors) >= 1
        assert any("participant" in e.lower() for e in errors)

    def test_multiple_errors(self):
        contrib = ContributionEvent(
            id=str(uuid4()),
            task_id=None,
            primary_entity_id=None,
            contribution_type="knowledge",
            description=None,
            evidence={},
            status=ContributionStatus.draft,
        )
        contrib.participants = []
        errors = contrib.validate_for_submission()
        assert len(errors) >= 4  # task, entity, description, evidence, participants
