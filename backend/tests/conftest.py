"""Integration test fixtures for PoCP AI Commons backend.

Usage:
    cd backend
    python -m pytest tests/ -v
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base, get_db
from main import app


# In-memory SQLite for tests
TEST_DATABASE_URL = "sqlite:///test_pocp.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """FastAPI test client with test database."""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def human_entity(db_session):
    """Create a test human entity."""
    from models.entity import Entity, EntityType, EntityStatus

    entity = Entity(
        entity_type=EntityType.human,
        name="TestUser",
        description="Test human entity",
        status=EntityStatus.active,
    )
    db_session.add(entity)
    db_session.flush()
    return entity


@pytest.fixture
def reviewer_entity(db_session):
    """Create a test reviewer entity (different from human_entity)."""
    from models.entity import Entity, EntityType, EntityStatus

    entity = Entity(
        entity_type=EntityType.human,
        name="Reviewer",
        description="Test reviewer entity",
        status=EntityStatus.active,
    )
    db_session.add(entity)
    db_session.flush()
    return entity


@pytest.fixture
def test_task(db_session, human_entity):
    """Create a test task."""
    from models.task import Task, TaskStatus

    task = Task(
        title="Test Task",
        description="A task for testing",
        sponsor_id=human_entity.id,
        status=TaskStatus.open,
    )
    db_session.add(task)
    db_session.flush()
    return task


@pytest.fixture
def agent_entity(db_session):
    """Create a test agent entity."""
    from models.entity import Entity, EntityType, EntityStatus

    entity = Entity(
        entity_type=EntityType.agent,
        name="TestAgent",
        description="Test agent entity",
        status=EntityStatus.active,
    )
    db_session.add(entity)
    db_session.flush()
    return entity


@pytest.fixture
def skill_entity(db_session):
    """Create a test skill entity."""
    from models.entity import Entity, EntityType, EntityStatus

    entity = Entity(
        entity_type=EntityType.skill,
        name="TestSkill",
        description="Test skill entity",
        status=EntityStatus.active,
    )
    db_session.add(entity)
    db_session.flush()
    return entity
