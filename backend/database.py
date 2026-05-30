import logging
import os
import time
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

logger = logging.getLogger(__name__)

SQLITE_BASELINE_REVISION = "72f32ab86a41"

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

    if is_sqlite():
        if _needs_sqlite_bootstrap():
            baseline_revision = _sqlite_bootstrap_revision()
            command.stamp(cfg, baseline_revision)
            logger.info("Bootstrapped legacy SQLite Alembic state to %s", baseline_revision)
        elif _sqlite_needs_revision_reconcile():
            command.stamp(cfg, SQLITE_BASELINE_REVISION)
            logger.info(
                "Reconciled SQLite Alembic state from schema drift to %s",
                SQLITE_BASELINE_REVISION,
            )

    command.upgrade(cfg, "head")
    if is_sqlite():
        _verify_sqlite_schema()
    logger.info("Alembic migrations applied (head)")


def _needs_sqlite_bootstrap() -> bool:
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    if "entities" not in table_names:
        return False
    if "alembic_version" not in table_names:
        return True

    with engine.connect() as conn:
        version_rows = conn.execute(text("SELECT version_num FROM alembic_version")).fetchall()
    return len(version_rows) == 0


def _sqlite_bootstrap_revision() -> str:
    inspector = inspect(engine)
    ledger_columns = {column["name"] for column in inspector.get_columns("ledger_records")}
    if {"prev_hash", "record_hash"}.issubset(ledger_columns):
        return "head"
    return SQLITE_BASELINE_REVISION


def _sqlite_needs_revision_reconcile() -> bool:
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    if "alembic_version" not in table_names or "ledger_records" not in table_names:
        return False

    with engine.connect() as conn:
        version_rows = conn.execute(text("SELECT version_num FROM alembic_version")).fetchall()

    if not version_rows:
        return False

    current_revision = version_rows[0][0]
    if current_revision != "a1b2c3d4e5f6":
        return False

    ledger_columns = {column["name"] for column in inspector.get_columns("ledger_records")}
    return not {"prev_hash", "record_hash"}.issubset(ledger_columns)


def _verify_sqlite_schema() -> None:
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    if "ledger_records" not in table_names:
        return

    ledger_columns = {column["name"] for column in inspector.get_columns("ledger_records")}
    required_columns = {"prev_hash", "record_hash"}
    missing_columns = required_columns - ledger_columns
    if missing_columns:
        raise RuntimeError(
            "SQLite schema verification failed for ledger_records; missing columns: "
            f"{sorted(missing_columns)}"
        )


def init_db() -> None:
    import models  # noqa: F401 — register metadata

    wait_for_db()
    run_migrations()


def reset_schema() -> None:
    """Drop all tables and re-apply migrations (PostgreSQL or SQLite)."""
    import models  # noqa: F401

    Base.metadata.drop_all(bind=engine)
    run_migrations()
