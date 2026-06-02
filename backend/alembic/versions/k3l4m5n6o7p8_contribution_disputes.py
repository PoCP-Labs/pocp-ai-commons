"""contribution_disputes table — challenge / appeal governance (PR-B)

Revision ID: k3l4m5n6o7p8
Revises: j2k3l4m5n6o7
Create Date: 2026-06-01
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "k3l4m5n6o7p8"
down_revision: Union[str, Sequence[str], None] = "j2k3l4m5n6o7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "contribution_disputes" in inspector.get_table_names():
        return
    op.create_table(
        "contribution_disputes",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("contribution_id", sa.String(length=36), nullable=False),
        sa.Column("parent_dispute_id", sa.String(length=36), nullable=True),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("challenger_entity_id", sa.String(length=36), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("evidence_hash", sa.String(length=128), nullable=True),
        sa.Column("resolution_entity_id", sa.String(length=36), nullable=True),
        sa.Column("resolution_note", sa.Text(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["contribution_id"], ["contribution_events.id"]),
        sa.ForeignKeyConstraint(["parent_dispute_id"], ["contribution_disputes.id"]),
        sa.ForeignKeyConstraint(["challenger_entity_id"], ["entities.id"]),
        sa.ForeignKeyConstraint(["resolution_entity_id"], ["entities.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_contribution_disputes_contribution_id", "contribution_disputes", ["contribution_id"])
    op.create_index("ix_contribution_disputes_status", "contribution_disputes", ["status"])


def downgrade() -> None:
    op.drop_index("ix_contribution_disputes_status", table_name="contribution_disputes")
    op.drop_index("ix_contribution_disputes_contribution_id", table_name="contribution_disputes")
    op.drop_table("contribution_disputes")
