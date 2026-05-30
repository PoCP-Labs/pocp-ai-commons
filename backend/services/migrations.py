"""Database migration utilities.

Auto-runs alembic migrations on startup.
"""

import logging
from pathlib import Path

from alembic import command
from alembic.config import Config

logger = logging.getLogger("pocp.migrations")


def run_migrations():
    """Run all pending alembic migrations on startup."""
    alembic_ini = Path(__file__).resolve().parent.parent / "alembic.ini"

    if not alembic_ini.exists():
        logger.warning("alembic.ini not found, skipping auto-migration")
        return

    alembic_cfg = Config(str(alembic_ini))

    try:
        command.upgrade(alembic_cfg, "head")
        logger.info("Database migrations applied successfully")
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise
