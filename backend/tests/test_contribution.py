"""Unit tests for contribution service logic."""

import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4

from models.contribution import (
    ContributionEvent,
    ContributionParticipant,
    ContributionStatus,
    ParticipantRole,
)
from models.entity import Entity, EntityType, EntityStatus
from models.wallet import Wallet, CreditTransaction, CreditType, ReputationScore
from services.contribution import (
    approve_contribution,
    grant_registration_credits,
    run_ai_verification,
)


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


class TestGrantRegistrationCredits:
    """Tests for the registration credits grant."""

    def test_grants_credits_to_new_human(self):
        db = MagicMock()
        entity = make_entity(EntityType.human, "Alice")

        # No existing wallet
        db.query.return_value.filter.return_value.first.return_value = None

        wallet = grant_registration_credits(db, entity)

        assert wallet is not None
        assert wallet.ai_credits == 100.0
        assert db.add.call_count >= 3  # wallet + transaction + ledger

    def test_no_credits_for_non_human(self):
        db = MagicMock()
        entity = make_entity(EntityType.agent, "HelperBot")

        wallet = grant_registration_credits(db, entity)

        assert wallet is None
        db.add.assert_not_called()

    def test_no_double_grant(self):
        db = MagicMock()
        entity = make_entity(EntityType.human, "Bob")

        # Existing wallet with credits already
        existing_wallet = Wallet(entity_id=entity.id, ai_credits=50.0)
        db.query.return_value.filter.return_value.first.return_value = existing_wallet

        wallet = grant_registration_credits(db, entity)

        # Returns existing wallet without adding credits
        assert wallet == existing_wallet


class TestRunAiVerification:
    """Tests for AI advisory verification."""

    def test_passing_score_sets_ai_verified(self):
        db = MagicMock()
        contribution = make_contribution()

        result = run_ai_verification(db, contribution, score=0.85)

        assert result.passed is True
        assert contribution.status == ContributionStatus.ai_verified
        db.add.assert_called_once()

    def test_failing_score_sets_rejected(self):
        db = MagicMock()
        contribution = make_contribution()

        result = run_ai_verification(db, contribution, score=0.50)

        assert result.passed is False
        assert contribution.status == ContributionStatus.rejected

    def test_threshold_is_07(self):
        db = MagicMock()
        contribution = make_contribution()

        # Exactly at threshold
        result = run_ai_verification(db, contribution, score=0.70)
        assert result.passed is True

        # Just below threshold
        contribution2 = make_contribution()
        result2 = run_ai_verification(db, contribution2, score=0.69)
        assert result2.passed is False


class TestApproveContribution:
    """Tests for human review and reward distribution."""

    def _setup_db(self, contributors):
        """Helper to set up a mock db with entities."""
        db = MagicMock()
        entity_map = {}
        for e in contributors:
            entity_map[e.id] = e

        def query_side_effect(model):
            mock_query = MagicMock()
            if model == Entity:
                mock_query.filter.return_value.first.side_effect = lambda: entity_map.get(
                    getattr(mock_query.filter.return_value, "_last_id", None)
                )

                def find_entity(entity_id):
                    mock_query.filter.return_value._last_id = entity_id
                    return entity_map.get(entity_id)

                mock_query.filter.return_value.first = find_entity
            return mock_query

        db.query.side_effect = query_side_effect
        return db, entity_map

    def test_rejects_self_approval(self):
        db, _ = self._setup_db([])
        contribution = make_contribution()

        with pytest.raises(ValueError, match="cannot approve their own"):
            approve_contribution(
                db, contribution, reviewer_id=contribution.primary_entity_id
            )

    def test_human_gets_cp_and_credits(self):
        db = MagicMock()
        human = make_entity(EntityType.human, "Alice")
        reviewer = make_entity(EntityType.human, "Reviewer")

        contribution = make_contribution(primary_entity_id=human.id)

        participant = ContributionParticipant(
            entity_id=human.id, role=ParticipantRole.creator, weight=1.0
        )
        contribution.participants = [participant]

        # Wallet starts empty
        wallet = Wallet(entity_id=human.id)
        # Entity lookup
        entity_map = {human.id: human, reviewer.id: reviewer}

        def query_side_effect(model):
            mock_query = MagicMock()
            if model == Entity:
                def filter_by_id(entity_id):
                    mock_query.filter.return_value.first = lambda: entity_map.get(
                        entity_id
                    )
                    return mock_query.filter.return_value
            elif model == Wallet:
                mock_query.filter.return_value.first.return_value = wallet
            return mock_query

        db.query.side_effect = query_side_effect

        rewards = approve_contribution(db, contribution, reviewer_id=reviewer.id)

        assert len(rewards["credits"]) == 1
        credit_reward = rewards["credits"][0]
        assert credit_reward["cp"] > 0
        assert credit_reward["ai_credits"] > 0

    def test_skill_gets_reputation(self):
        db = MagicMock()
        human = make_entity(EntityType.human, "Alice")
        reviewer = make_entity(EntityType.human, "Reviewer")
        skill = make_entity(EntityType.skill, "CodeReviewSkill")

        contribution = make_contribution(primary_entity_id=human.id)

        participant_human = ContributionParticipant(
            entity_id=human.id, role=ParticipantRole.creator, weight=0.8
        )
        participant_skill = ContributionParticipant(
            entity_id=skill.id, role=ParticipantRole.skill_provider, weight=0.2
        )
        contribution.participants = [participant_human, participant_skill]

        wallet = Wallet(entity_id=human.id)
        entity_map = {human.id: human, reviewer.id: reviewer, skill.id: skill}

        def query_side_effect(model):
            mock_query = MagicMock()
            if model == Entity:
                def filter_by_id(entity_id):
                    mock_query.filter.return_value.first = lambda: entity_map.get(
                        entity_id
                    )
                    return mock_query.filter.return_value
            elif model == Wallet:
                mock_query.filter.return_value.first.return_value = wallet
            elif model == ReputationScore:
                mock_query.filter.return_value.first.return_value = None
            return mock_query

        db.query.side_effect = query_side_effect

        rewards = approve_contribution(db, contribution, reviewer_id=reviewer.id)

        assert len(rewards["reputation"]) >= 1
        skill_rep = [r for r in rewards["reputation"] if r["entity_id"] == skill.id]
        assert len(skill_rep) == 1
        assert skill_rep[0]["category"] == "skill"

    def test_agent_gets_reputation(self):
        db = MagicMock()
        human = make_entity(EntityType.human, "Alice")
        reviewer = make_entity(EntityType.human, "Reviewer")
        agent = make_entity(EntityType.agent, "StudyAgent")

        contribution = make_contribution(primary_entity_id=human.id)

        participant_human = ContributionParticipant(
            entity_id=human.id, role=ParticipantRole.creator, weight=0.7
        )
        participant_agent = ContributionParticipant(
            entity_id=agent.id, role=ParticipantRole.executor, weight=0.3
        )
        contribution.participants = [participant_human, participant_agent]

        wallet = Wallet(entity_id=human.id)
        entity_map = {human.id: human, reviewer.id: reviewer, agent.id: agent}

        def query_side_effect(model):
            mock_query = MagicMock()
            if model == Entity:
                def filter_by_id(entity_id):
                    mock_query.filter.return_value.first = lambda: entity_map.get(
                        entity_id
                    )
                    return mock_query.filter.return_value
            elif model == Wallet:
                mock_query.filter.return_value.first.return_value = wallet
            elif model == ReputationScore:
                mock_query.filter.return_value.first.return_value = None
            return mock_query

        db.query.side_effect = query_side_effect

        rewards = approve_contribution(db, contribution, reviewer_id=reviewer.id)

        agent_rep = [r for r in rewards["reputation"] if r["entity_id"] == agent.id]
        assert len(agent_rep) == 1
        assert agent_rep[0]["category"] == "agent"
