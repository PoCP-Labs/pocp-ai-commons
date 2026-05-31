"""external inspiration records

Revision ID: f7a8b9c0d1e2
Revises: e6f7a8b9c0d1
Create Date: 2026-05-30
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f7a8b9c0d1e2"
down_revision: Union[str, Sequence[str], None] = "e6f7a8b9c0d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "external_inspiration_records",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("inspiration_slug", sa.String(length=64), nullable=False),
        sa.Column("contribution_id", sa.String(length=64), nullable=False),
        sa.Column("entity_id", sa.String(length=36), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("relationship", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column(
            "pocp_modules",
            sa.JSON().with_variant(postgresql.JSONB(), "postgresql"),
            nullable=True,
        ),
        sa.Column(
            "api_paths",
            sa.JSON().with_variant(postgresql.JSONB(), "postgresql"),
            nullable=True,
        ),
        sa.Column(
            "proof_layers",
            sa.JSON().with_variant(postgresql.JSONB(), "postgresql"),
            nullable=True,
        ),
        sa.Column("integration_section", sa.Integer(), nullable=True),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column(
            "metadata",
            sa.JSON().with_variant(postgresql.JSONB(), "postgresql"),
            nullable=True,
        ),
        sa.Column("recorded_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["entity_id"], ["entities.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_external_inspiration_records_inspiration_slug",
        "external_inspiration_records",
        ["inspiration_slug"],
        unique=False,
    )
    op.create_index(
        "ix_external_inspiration_records_contribution_id",
        "external_inspiration_records",
        ["contribution_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_external_inspiration_records_contribution_id",
        table_name="external_inspiration_records",
    )
    op.drop_index(
        "ix_external_inspiration_records_inspiration_slug",
        table_name="external_inspiration_records",
    )
    op.drop_table("external_inspiration_records")
