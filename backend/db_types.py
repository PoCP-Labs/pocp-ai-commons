"""Cross-database column types (PostgreSQL-first, SQLite-compatible for local dev)."""

import enum

from sqlalchemy import JSON, Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB

JsonDocument = JSON().with_variant(JSONB(), "postgresql")


def pocp_enum(enum_cls: type[enum.Enum], *, length: int = 32) -> SAEnum:
    """Store enums as VARCHAR so SQLite dev and PostgreSQL prod share one Alembic history."""
    return SAEnum(
        enum_cls,
        values_callable=lambda obj: [member.value for member in obj],
        native_enum=False,
        length=length,
    )
