"""Revision ID: m5n6o7p8q9r0
Revises: l4m5n6o7p8q9
Create Date: 2026-06-01 — Agent Studio memory vault
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "m5n6o7p8q9r0"
down_revision: Union[str, Sequence[str], None] = "l4m5n6o7p8q9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "agent_studio_memories" in inspector.get_table_names():
        return

    op.create_table(
        "agent_studio_memories",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("scope", sa.String(length=32), nullable=False),
        sa.Column("agent_entity_id", sa.String(length=36), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("source_type", sa.String(length=64), nullable=True),
        sa.Column("source_id", sa.String(length=36), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("importance", sa.Float(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["agent_entity_id"], ["entities.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_studio_memories_agent", "agent_studio_memories", ["agent_entity_id"])
    op.create_index("ix_agent_studio_memories_scope", "agent_studio_memories", ["scope"])
    op.create_index("ix_agent_studio_memories_kind", "agent_studio_memories", ["kind"])


def downgrade() -> None:
    op.drop_table("agent_studio_memories")
