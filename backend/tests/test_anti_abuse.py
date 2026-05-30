"""
PoCP AI Commons — Anti-Abuse Tests
=====================================
Tests for abuse prevention: missing evidence rejection, daily limits,
self-approval blocking, and other anti-gaming safeguards.

Run with:
    pytest tests/test_anti_abuse.py -v
"""

import uuid
from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base, get_db
from main import app
from models.contribution import (
    ContributionEvent,
    ContributionParticipant,
    ContributionStatus,
    HumanReview,
    ParticipantRole,
)
from models.entity import Entity, EntityStatus, EntityType
from models.task import Task, TaskStatus
from models.wallet import Wallet, CreditTransaction, CreditType
from services.contribution import (
    approve_contribution,
    grant_registration_credits,
    run_ai_verification,
)

# Test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_pocp_anti_abuse.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db():
    """Create a clean database session for each test."""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        import os
        if os.path.exists("./test_pocp_anti_abuse.db"):
            os.remove("./test_pocp_anti_abuse.db")


# ---------------------------------------------------------------------------
# Helper: create a fully set up contribution ready for approval
# ---------------------------------------------------------------------------
def _create_full_setup(db):
    """Create entities, task, and contribution for testing."""
    alice = Entity(
        entity_type=EntityType.human,
        name="Alice",
        description="Test contributor",
        status=EntityStatus.active,
    )
    bob = Entity(
        entity_type=EntityType.human,
        name="Bob",
        description="Test reviewer",
        status=EntityStatus.active,
    )
    alice.creator_id = bob.id
    db.add_all([alice, bob])
    db.flush()

    task = Task(
        title="Test Task",
        description="A test contribution task",
        sponsor_id=bob.id,
        status=TaskStatus.open,
    )
    db.add(task)
    db.flush()

    contribution = ContributionEvent(
        task_id=task.id,
        primary_entity_id=alice.id,
        contribution_type="knowledge",
        description="Test contribution",
        evidence={
            "content": "Some meaningful work product demonstrating value.",
            "skills_used": [],
        },
        status=ContributionStatus.submitted,
    )
    db.add(contribution)
    db.flush()

    # Add participant
    participant = ContributionParticipant(
        contribution_id=contribution.id,
        entity_id=alice.id,
        role=ParticipantRole.creator,
        weight=0.8,
        evidence={"action": "created content"},
    )
    db.add(participant)
    db.flush()

    return {
        "db": db,
        "alice": alice,
        "bob": bob,
        "task": task,
        "contribution": contribution,
        "participant": participant,
    }


# ---------------------------------------------------------------------------
# Test 1: REJECT — contribution with empty evidence
# ---------------------------------------------------------------------------
def test_reject_empty_evidence(db):
    """A contribution with no evidence should be rejectable."""
    alice = Entity(entity_type=EntityType.human, name="Alice")
    bob = Entity(entity_type=EntityType.human, name="Bob")
    db.add_all([alice, bob])
    db.flush()

    task = Task(title="Empty evidence task", sponsor_id=bob.id, status=TaskStatus.open)
    db.add(task)
    db.flush()

    # Empty evidence dict
    contribution = ContributionEvent(
        task_id=task.id,
        primary_entity_id=alice.id,
        contribution_type="knowledge",
        description="Low effort submission",
        evidence={},
        status=ContributionStatus.submitted,
    )
    db.add(contribution)
    db.flush()

    db.add(ContributionParticipant(
        contribution_id=contribution.id,
        entity_id=alice.id,
        role=ParticipantRole.creator,
        weight=1.0,
    ))
    db.flush()

    # AI verifier should flag this
    ai_result = run_ai_verification(
        db, contribution, score=0.15,
        feedback="No evidence provided. Rejecting empty submission.",
    )
    assert ai_result.passed is False
    assert contribution.status == ContributionStatus.rejected


# ---------------------------------------------------------------------------
# Test 2: REJECT — contribution with only empty/trivial content
# ---------------------------------------------------------------------------
def test_reject_trivial_content(db):
    """A contribution with trivial, meaningless content should be rejectable."""
    alice = Entity(entity_type=EntityType.human, name="Alice")
    bob = Entity(entity_type=EntityType.human, name="Bob")
    db.add_all([alice, bob])
    db.flush()

    task = Task(title="Trivial test", sponsor_id=bob.id, status=TaskStatus.open)
    db.add(task)
    db.flush()

    contribution = ContributionEvent(
        task_id=task.id,
        primary_entity_id=alice.id,
        contribution_type="knowledge",
        description="Test",
        evidence={"content": "hello world 123"},
        status=ContributionStatus.submitted,
    )
    db.add(contribution)
    db.flush()

    db.add(ContributionParticipant(
        contribution_id=contribution.id,
        entity_id=alice.id,
        role=ParticipantRole.creator,
        weight=1.0,
    ))
    db.flush()

    ai_result = run_ai_verification(
        db, contribution, score=0.25,
        feedback="Content is trivial. Contains no meaningful work.",
    )
    assert ai_result.passed is False
    assert contribution.status == ContributionStatus.rejected


# ---------------------------------------------------------------------------
# Test 3: BLOCK — self-approval (contributor == reviewer)
# ---------------------------------------------------------------------------
def test_block_self_approval(db):
    """A contributor should not be able to approve their own work."""
    alice = Entity(entity_type=EntityType.human, name="Alice")
    db.add(alice)
    db.flush()

    task = Task(title="Self-approval test", sponsor_id=alice.id, status=TaskStatus.open)
    db.add(task)
    db.flush()

    contribution = ContributionEvent(
        task_id=task.id,
        primary_entity_id=alice.id,
        contribution_type="knowledge",
        description="Self-approval attempt",
        evidence={"content": "Some work"},
        status=ContributionStatus.submitted,
    )
    db.add(contribution)
    db.flush()

    db.add(ContributionParticipant(
        contribution_id=contribution.id,
        entity_id=alice.id,
        role=ParticipantRole.creator,
        weight=1.0,
    ))
    db.flush()

    # Alice is both the creator AND trying to be the reviewer
    # contributor's primary_entity_id == reviewer_id
    run_ai_verification(db, contribution, score=0.9, feedback="Looks good.")

    # attempt to approve
    with pytest.raises(ValueError, match="self-approval|reviewer.*same|cannot approve own"):
        approve_contribution(
            db, contribution,
            reviewer_id=alice.id,  # same as primary_entity_id
            feedback="I approve my own work!",
        )

    # The contribution should NOT be approved
    db.refresh(contribution)
    assert contribution.status != ContributionStatus.approved


# ---------------------------------------------------------------------------
# Test 4: BLOCK — approval from non-human entity
# ---------------------------------------------------------------------------
def test_block_non_human_reviewer(db):
    """Only human entities should be able to approve contributions."""
    alice = Entity(entity_type=EntityType.human, name="Alice")
    agent_entity = Entity(entity_type=EntityType.agent, name="AutomaticApprover")
    db.add_all([alice, agent_entity])
    db.flush()

    task = Task(title="Non-human reviewer", sponsor_id=alice.id, status=TaskStatus.open)
    db.add(task)
    db.flush()

    contribution = ContributionEvent(
        task_id=task.id,
        primary_entity_id=alice.id,
        contribution_type="knowledge",
        description="Agent tries to approve",
        evidence={"content": "Some content"},
        status=ContributionStatus.submitted,
    )
    db.add(contribution)
    db.flush()

    db.add(ContributionParticipant(
        contribution_id=contribution.id,
        entity_id=alice.id,
        role=ParticipantRole.creator,
        weight=1.0,
    ))
    db.flush()

    run_ai_verification(db, contribution, score=0.85, feedback="Passes AI check.")

    # An agent entity should not be able to review
    with pytest.raises(ValueError, match="human.*reviewer|only human|reviewer.*human"):
        approve_contribution(
            db, contribution,
            reviewer_id=agent_entity.id,
            feedback="Auto-approved.",
        )

    db.refresh(contribution)
    assert contribution.status != ContributionStatus.approved


# ---------------------------------------------------------------------------
# Test 5: REJECT — approval without prior AI verification
# ---------------------------------------------------------------------------
def test_block_approval_without_ai_verification(db):
    """A contribution should pass AI verification before human review."""
    alice = Entity(entity_type=EntityType.human, name="Alice")
    bob = Entity(entity_type=EntityType.human, name="Bob")
    db.add_all([alice, bob])
    db.flush()

    task = Task(title="Skip AI test", sponsor_id=bob.id, status=TaskStatus.open)
    db.add(task)
    db.flush()

    contribution = ContributionEvent(
        task_id=task.id,
        primary_entity_id=alice.id,
        contribution_type="knowledge",
        description="Skip AI verification",
        evidence={"content": "Some content"},
        status=ContributionStatus.submitted,
    )
    db.add(contribution)
    db.flush()

    db.add(ContributionParticipant(
        contribution_id=contribution.id,
        entity_id=alice.id,
        role=ParticipantRole.creator,
        weight=1.0,
    ))
    db.flush()

    # Bob tries to approve without AI verification
    with pytest.raises(ValueError, match="ai_verified|must pass AI|not verified"):
        approve_contribution(
            db, contribution,
            reviewer_id=bob.id,
            feedback="Approved without AI check.",
        )

    db.refresh(contribution)
    assert contribution.status == ContributionStatus.submitted


# ---------------------------------------------------------------------------
# Test 6: NORMAL — standard approve flow succeeds
# ---------------------------------------------------------------------------
def test_standard_approve_flow(db):
    """A properly submitted, AI-verified contribution should approve correctly."""
    setup = _create_full_setup(db)
    contribution = setup["contribution"]

    # Step 1: AI verification passes
    run_ai_verification(db, contribution, score=0.85)
    assert contribution.status == ContributionStatus.ai_verified

    # Step 2: Different human approves
    db.refresh(contribution)
    approval = approve_contribution(
        db, contribution,
        reviewer_id=setup["bob"].id,
        feedback="Approved. Good work.",
    )

    assert approval is not None
    db.refresh(contribution)
    assert contribution.status == ContributionStatus.approved

    # Check rewards were distributed
    rewards = approval
    assert len(rewards["credits"]) > 0 or len(rewards["reputation"]) > 0


# ---------------------------------------------------------------------------
# Test 7: Registration credits only issued once
# ---------------------------------------------------------------------------
def test_registration_credits_once(db):
    """Registration credits should only be issued to new human entities once."""
    alice = Entity(entity_type=EntityType.human, name="Alice")
    db.add(alice)
    db.flush()

    first = grant_registration_credits(db, alice)
    assert first is not None
    assert first.ai_credits > 0

    # Second call should return the existing wallet without adding more credits
    second = grant_registration_credits(db, alice)
    assert second is not None
    assert second.id == first.id
    assert second.ai_credits == first.ai_credits


# ---------------------------------------------------------------------------
# Test 8: Non-human entities don't get registration credits
# ---------------------------------------------------------------------------
def test_no_credits_for_non_human(db):
    """Agents, skills, and LLMs should not receive registration credits."""
    agent = Entity(entity_type=EntityType.agent, name="BotAgent")
    skill = Entity(entity_type=EntityType.skill, name="SkillProvider")
    llm = Entity(entity_type=EntityType.llm, name="LLMProvider")
    db.add_all([agent, skill, llm])
    db.flush()

    for entity in [agent, skill, llm]:
        result = grant_registration_credits(db, entity)
        assert result is None, f"{entity.entity_type} should not get registration credits"
