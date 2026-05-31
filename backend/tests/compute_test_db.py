"""Shared in-memory SQLite session for compute job tests."""

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import models  # noqa: F401 — register ORM tables on Base
from database import Base


def make_compute_test_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()
