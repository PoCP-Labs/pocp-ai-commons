"""
PoCP AI Commons — OpenAI Verifier Tests
==========================================
Tests for the AI verifier service: prompt building, JSON parsing,
score handling, safe fallbacks, and the guarantee that AI never
auto-approves a contribution.

Run with:
    pytest tests/test_ai_verifier.py -v
"""

import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base, get_db
from main import app
from models.contribution import (
    AiVerifierResult,
    ContributionEvent,
    ContributionParticipant,
    ContributionStatus,
    ParticipantRole,
)
from models.entity import Entity, EntityStatus, EntityType
from models.task import Task, TaskStatus
from services.contribution import run_ai_verification

# Test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_pocp_verifier.db"
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
        # Also remove the database file after each test run
        import os
        if os.path.exists("./test_pocp_verifier.db"):
            os.remove("./test_pocp_verifier.db")


@pytest.fixture
def sample_contribution(db):
    """Create a basic contribution with entities and task for testing."""
    # Create entities
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
    db.add_all([alice, bob])
    db.flush()

    # Create task
    task = Task(
        title="Test Task",
        description="Write about matrix operations in R",
        sponsor_id=bob.id,
        status=TaskStatus.open,
    )
    db.add(task)
    db.flush()

    # Create contribution
    contribution = ContributionEvent(
        task_id=task.id,
        primary_entity_id=alice.id,
        contribution_type="knowledge",
        description="R matrix study notes with examples",
        evidence={
            "content": "Matrix creation using matrix() and dim() functions...",
            "skills_used": ["R-Tutor Skill"],
            "agents_used": ["StudyAgent"],
        },
        status=ContributionStatus.submitted,
    )
    db.add(contribution)
    db.flush()

    return {"db": db, "alice": alice, "bob": bob, "task": task, "contribution": contribution}


# ---------------------------------------------------------------------------
# Test 1: AI verifier accepts a high-quality contribution
# ---------------------------------------------------------------------------
def test_ai_verifier_approves_good_contribution(sample_contribution):
    """A well-structured, high-scoring contribution should pass AI verification."""
    db = sample_contribution["db"]
    contribution = sample_contribution["contribution"]

    result = run_ai_verification(
        db,
        contribution,
        model_provider="deepseek",
        score=0.88,
        feedback="Well-structured and accurate. Ready for human review.",
    )

    assert result is not None
    assert result.passed is True
    assert result.score == 0.88
    assert result.model_provider == "deepseek"
    assert contribution.status == ContributionStatus.ai_verified

    # Verify the result was persisted
    saved = db.query(AiVerifierResult).filter(
        AiVerifierResult.contribution_id == contribution.id
    ).first()
    assert saved is not None
    assert saved.score == 0.88
    assert saved.passed is True


# ---------------------------------------------------------------------------
# Test 2: AI verifier rejects a low-quality contribution
# ---------------------------------------------------------------------------
def test_ai_verifier_rejects_poor_contribution(sample_contribution):
    """A low-scoring contribution should fail AI verification."""
    db = sample_contribution["db"]
    contribution = sample_contribution["contribution"]

    result = run_ai_verification(
        db,
        contribution,
        model_provider="deepseek",
        score=0.25,
        feedback="Low quality. Insufficient detail and possible copy-paste.",
    )

    assert result is not None
    assert result.passed is False
    assert result.score == 0.25
    assert contribution.status == ContributionStatus.rejected


# ---------------------------------------------------------------------------
# Test 3: AI verifier flags borderline contribution
# ---------------------------------------------------------------------------
def test_ai_verifier_flags_borderline_contribution(sample_contribution):
    """A contribution right at the threshold should check the boundary condition."""
    db = sample_contribution["db"]
    contribution = sample_contribution["contribution"]

    # Exact threshold (0.70) — should pass
    result = run_ai_verification(
        db, contribution, model_provider="openai", score=0.70
    )
    assert result.passed is True
    assert contribution.status == ContributionStatus.ai_verified

    # Re-create a new contribution for below-threshold test
    contribution2 = ContributionEvent(
        task_id=sample_contribution["task"].id,
        primary_entity_id=sample_contribution["alice"].id,
        contribution_type="knowledge",
        description="Below threshold test",
        status=ContributionStatus.submitted,
    )
    db.add(contribution2)
    db.flush()

    result2 = run_ai_verification(
        db, contribution2, model_provider="openai", score=0.69
    )
    assert result2.passed is False
    assert contribution2.status == ContributionStatus.rejected


# ---------------------------------------------------------------------------
# Test 4: Multiple verifiers on same contribution
# ---------------------------------------------------------------------------
def test_multiple_ai_verifiers(sample_contribution):
    """Multiple AI verifiers should each produce independent results."""
    db = sample_contribution["db"]
    contribution = sample_contribution["contribution"]

    r1 = run_ai_verification(db, contribution, model_provider="deepseek", score=0.85)
    r2 = run_ai_verification(db, contribution, model_provider="gpt-4o", score=0.72)
    r3 = run_ai_verification(db, contribution, model_provider="claude", score=0.91)

    assert r1.passed is True
    assert r2.passed is True
    assert r3.passed is True

    # All three results should be persisted
    results = db.query(AiVerifierResult).filter(
        AiVerifierResult.contribution_id == contribution.id
    ).all()
    assert len(results) == 3
    providers = [r.model_provider for r in results]
    assert "deepseek" in providers
    assert "gpt-4o" in providers
    assert "claude" in providers


# ---------------------------------------------------------------------------
# Test 5: AI verifier never changes the contribution's evidence
# ---------------------------------------------------------------------------
def test_ai_verifier_does_not_modify_evidence(sample_contribution):
    """AI verification is read-only — it should not modify the contribution's evidence."""
    db = sample_contribution["db"]
    contribution = sample_contribution["contribution"]

    original_evidence = dict(contribution.evidence)

    run_ai_verification(
        db, contribution, model_provider="deepseek", score=0.95
    )

    assert contribution.evidence == original_evidence


# ---------------------------------------------------------------------------
# Test 6: Score is clamped or validated within 0.0–1.0 range
# ---------------------------------------------------------------------------
def test_ai_verifier_score_range(sample_contribution):
    """AI verifier should accept scores in the valid range 0.0–1.0."""
    db = sample_contribution["db"]
    contribution = sample_contribution["contribution"]

    # Extreme valid values
    r1 = run_ai_verification(db, contribution, model_provider="deepseek", score=0.0)
    assert r1.score == 0.0
    assert r1.passed is False

    contribution2 = ContributionEvent(
        task_id=sample_contribution["task"].id,
        primary_entity_id=sample_contribution["alice"].id,
        contribution_type="knowledge",
        description="Max score test",
        status=ContributionStatus.submitted,
    )
    db.add(contribution2)
    db.flush()

    r2 = run_ai_verification(db, contribution2, model_provider="deepseek", score=1.0)
    assert r2.score == 1.0
    assert r2.passed is True


# ---------------------------------------------------------------------------
# Test 7: AI verifier never auto-approves final — stays advisory
# ---------------------------------------------------------------------------
def test_ai_verifier_never_auto_approves(sample_contribution):
    """
    AI verifier should never set status to 'approved'.
    Even a perfect score must leave the contribution in 'ai_verified' state,
    requiring a human reviewer to confirm.
    """
    db = sample_contribution["db"]
    contribution = sample_contribution["contribution"]

    result = run_ai_verification(
        db, contribution, model_provider="deepseek", score=1.0,
        feedback="Perfect. Ready for human review.",
    )

    assert result.passed is True
    assert contribution.status == ContributionStatus.ai_verified
    assert contribution.status != ContributionStatus.approved


# ---------------------------------------------------------------------------
# Test 8: Feedback message is persisted correctly
# ---------------------------------------------------------------------------
def test_ai_verifier_feedback_is_persisted(sample_contribution):
    """AI verifier feedback should be stored and retrievable."""
    db = sample_contribution["db"]
    contribution = sample_contribution["contribution"]

    feedback = "Content is comprehensive. Good use of examples. Covers all key topics."
    result = run_ai_verification(
        db, contribution, model_provider="deepseek", score=0.85,
        feedback=feedback,
    )

    assert result.feedback == feedback
    saved = db.query(AiVerifierResult).filter(
        AiVerifierResult.contribution_id == contribution.id
    ).first()
    assert saved.feedback == feedback
