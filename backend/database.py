import logging
import os
import time
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_DIR.mkdir(exist_ok=True)

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{DATA_DIR / 'pocp.db'}",
)

WAIT_FOR_DB = os.getenv("POCP_WAIT_FOR_DB", "true").lower() in ("1", "true", "yes")
WAIT_FOR_DB_SECONDS = int(os.getenv("POCP_WAIT_FOR_DB_SECONDS", "60"))


def is_sqlite() -> bool:
    return DATABASE_URL.startswith("sqlite")


def is_postgresql() -> bool:
    return DATABASE_URL.startswith("postgresql")


def database_dialect() -> str:
    if is_postgresql():
        return "postgresql"
    if is_sqlite():
        return "sqlite"
    return DATABASE_URL.split(":", 1)[0]


def _engine_kwargs() -> dict:
    kwargs: dict = {}
    if is_sqlite():
        kwargs["connect_args"] = {"check_same_thread": False}
    elif is_postgresql():
        kwargs.update(
            pool_pre_ping=True,
            pool_size=int(os.getenv("POCP_DB_POOL_SIZE", "5")),
            max_overflow=int(os.getenv("POCP_DB_MAX_OVERFLOW", "10")),
        )
    return kwargs


engine = create_engine(DATABASE_URL, **_engine_kwargs())
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_database() -> str:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return "ok"
    except Exception as exc:
        return f"error: {exc}"


def wait_for_db() -> None:
    if not WAIT_FOR_DB:
        return
    deadline = time.monotonic() + WAIT_FOR_DB_SECONDS
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("Database ready (%s)", database_dialect())
            return
        except Exception as exc:
            last_error = exc
            time.sleep(1)
    raise RuntimeError(
        f"Database unavailable after {WAIT_FOR_DB_SECONDS}s ({database_dialect()}): {last_error}"
    ) from last_error


def run_migrations() -> None:
    from alembic import command
    from alembic.config import Config

    alembic_ini = Path(__file__).resolve().parent / "alembic.ini"
    cfg = Config(str(alembic_ini))
    cfg.set_main_option("sqlalchemy.url", DATABASE_URL)
    command.upgrade(cfg, "head")
    logger.info("Alembic migrations applied (head)")


def init_db() -> None:
    import models  # noqa: F401 — register metadata

    wait_for_db()
    run_migrations()


def reset_schema() -> None:
    """Drop all tables and re-apply migrations (PostgreSQL or SQLite)."""
    import models  # noqa: F401

    Base.metadata.drop_all(bind=engine)
    run_migrations()
