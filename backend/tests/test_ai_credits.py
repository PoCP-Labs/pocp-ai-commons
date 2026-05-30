"""
PoCP AI Commons — AI Credits Burn Tests
==========================================
Tests for AI Credits consumption: chat consumes credits,
insufficient credits blocks usage, usage log is created.

Run with:
    pytest tests/test_ai_credits.py -v
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models.entity import Entity, EntityStatus, EntityType
from models.wallet import CreditTransaction, CreditType, Wallet
from services.contribution import grant_registration_credits, spend_ai_credits

# Test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_pocp_credits.db"
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
        if os.path.exists("./test_pocp_credits.db"):
            os.remove("./test_pocp_credits.db")


@pytest.fixture
def human_with_credits(db):
    """Create a human entity with registration credits."""
    entity = Entity(
        entity_type=EntityType.human,
        name="Alice",
        description="Test user",
        status=EntityStatus.active,
    )
    db.add(entity)
    db.flush()
    grant_registration_credits(db, entity)
    db.refresh(entity)
    return entity


# ---------------------------------------------------------------------------
# Test 1: Chat consumes AI Credits
# ---------------------------------------------------------------------------
def test_chat_consumes_credits(human_with_credits, db):
    """Using AI chat should deduct AI Credits from the user's wallet."""
    entity = human_with_credits
    wallet = db.query(Wallet).filter(Wallet.entity_id == entity.id).first()
    initial_credits = wallet.ai_credits
    assert initial_credits > 0

    # Spend 10 credits on a chat message
    cost = 10.0
    result = spend_ai_credits(
        db,
        entity_id=entity.id,
        amount=cost,
        reason="AI chat message: Explain R matrix operations",
    )

    assert result["spent"] == cost
    assert result["remaining"] == initial_credits - cost
    assert "transaction_id" in result
    assert result["reason"] == "AI chat message: Explain R matrix operations"

    # Verify balance updated in DB
    db.refresh(wallet)
    assert wallet.ai_credits == initial_credits - cost


# ---------------------------------------------------------------------------
# Test 2: Credits transaction is logged
# ---------------------------------------------------------------------------
def test_credit_transaction_logged(human_with_credits, db):
    """Each AI Credits spend should create a CreditTransaction record."""
    entity = human_with_credits
    wallet = db.query(Wallet).filter(Wallet.entity_id == entity.id).first()

    spend_ai_credits(db, entity_id=entity.id, amount=5.0, reason="Code analysis")
    spend_ai_credits(db, entity_id=entity.id, amount=3.0, reason="Grammar check")
    spend_ai_credits(db, entity_id=entity.id, amount=2.0, reason="Summary")

    transactions = (
        db.query(CreditTransaction)
        .filter(CreditTransaction.wallet_id == wallet.id)
        .order_by(CreditTransaction.created_at.desc())
        .all()
    )

    assert len(transactions) == 3

    # Most recent first
    assert transactions[0].amount == -2.0
    assert transactions[0].credit_type == CreditType.ai_credits
    assert transactions[0].reason == "Summary"

    assert transactions[2].amount == -5.0
    assert transactions[2].reason == "Code analysis"


# ---------------------------------------------------------------------------
# Test 3: Insufficient credits blocks usage
# ---------------------------------------------------------------------------
def test_insufficient_credits_blocks_usage(human_with_credits, db):
    """Spending more credits than available should raise an error."""
    entity = human_with_credits
    wallet = db.query(Wallet).filter(Wallet.entity_id == entity.id).first()

    # Try to spend more than available
    too_much = wallet.ai_credits + 1

    with pytest.raises(ValueError, match="Insufficient AI Credits"):
        spend_ai_credits(
            db,
            entity_id=entity.id,
            amount=too_much,
            reason="Attempting to overdraw",
        )

    # Balance should remain unchanged
    db.refresh(wallet)
    assert wallet.ai_credits > 0


# ---------------------------------------------------------------------------
# Test 4: Zero or negative amount is rejected
# ---------------------------------------------------------------------------
def test_invalid_amount_rejected(human_with_credits, db):
    """Spending zero or negative AI Credits should raise an error."""
    with pytest.raises(ValueError, match="Amount must be greater than zero"):
        spend_ai_credits(db, entity_id=human_with_credits.id, amount=0.0)

    with pytest.raises(ValueError, match="Amount must be greater than zero"):
        spend_ai_credits(db, entity_id=human_with_credits.id, amount=-5.0)

    # Verify balance untouched
    wallet = db.query(Wallet).filter(Wallet.entity_id == human_with_credits.id).first()
    assert wallet.ai_credits > 0


# ---------------------------------------------------------------------------
# Test 5: Entity without wallet cannot spend
# ---------------------------------------------------------------------------
def test_no_wallet_rejected(db):
    """An entity without a wallet should not be able to spend credits."""
    entity = Entity(
        entity_type=EntityType.human,
        name="NoWalletUser",
        status=EntityStatus.active,
    )
    db.add(entity)
    db.flush()

    with pytest.raises(ValueError, match="Wallet not found"):
        spend_ai_credits(db, entity_id=entity.id, amount=5.0)


# ---------------------------------------------------------------------------
# Test 6: Remaining balance is accurate after multiple spends
# ---------------------------------------------------------------------------
def test_remaining_balance_accurate(human_with_credits, db):
    """The remaining balance should reflect all cumulative spends correctly."""
    entity = human_with_credits
    wallet = db.query(Wallet).filter(Wallet.entity_id == entity.id).first()
    initial = wallet.ai_credits

    # Spend in sequence
    spends = [10.0, 20.0, 5.0, 15.0]
    total_spent = sum(spends)
    assert initial > total_spent  # Sanity check for test setup

    for amount in spends:
        result = spend_ai_credits(db, entity_id=entity.id, amount=amount)
        assert result["remaining"] == wallet.ai_credits  # already deducted

    db.refresh(wallet)
    assert wallet.ai_credits == pytest.approx(initial - total_spent)


# ---------------------------------------------------------------------------
# Test 7: Agent and skill entities can have wallets and spend credits
# ---------------------------------------------------------------------------
def test_agent_can_have_wallet(db):
    """Non-human entities with wallets should also be able to spend credits."""
    agent = Entity(
        entity_type=EntityType.agent,
        name="StudyAgent",
        status=EntityStatus.active,
    )
    db.add(agent)
    db.flush()

    # Manually add credits to agent's wallet (no registration grant for agents)
    wallet = Wallet(entity_id=agent.id, ai_credits=50.0)
    db.add(wallet)
    db.flush()

    result = spend_ai_credits(db, entity_id=agent.id, amount=10.0)
    assert result["spent"] == 10.0

    db.refresh(wallet)
    assert wallet.ai_credits == 40.0
