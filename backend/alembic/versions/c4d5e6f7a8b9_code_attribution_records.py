"""code attribution records

Revision ID: c4d5e6f7a8b9
Revises: b2c3d4e5f6a7
Create Date: 2026-05-30
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c4d5e6f7a8b9"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "code_attribution_records",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("builder_slug", sa.String(length=64), nullable=False),
        sa.Column("entity_id", sa.String(length=36), nullable=True),
        sa.Column("path", sa.String(length=512), nullable=False),
        sa.Column("lines_count", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("commit_sha", sa.String(length=64), nullable=True),
        sa.Column("pr_url", sa.String(length=512), nullable=True),
        sa.Column(
            "metadata",
            sa.JSON().with_variant(postgresql.JSONB(), "postgresql"),
            nullable=True,
        ),
        sa.Column("contribution_event_id", sa.String(length=36), nullable=True),
        sa.Column("recorded_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["contribution_event_id"], ["contribution_events.id"]),
        sa.ForeignKeyConstraint(["entity_id"], ["entities.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_code_attribution_records_builder_slug",
        "code_attribution_records",
        ["builder_slug"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_code_attribution_records_builder_slug", table_name="code_attribution_records")
    op.drop_table("code_attribution_records")
