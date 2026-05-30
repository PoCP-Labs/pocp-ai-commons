"""agent feedback registry (ERC-8004 off-chain pattern)

Revision ID: d5e6f7a8b9c0
Revises: c4d5e6f7a8b9
Create Date: 2026-05-30
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d5e6f7a8b9c0"
down_revision: Union[str, Sequence[str], None] = "c4d5e6f7a8b9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "agent_feedback",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("agent_entity_id", sa.String(length=36), nullable=False),
        sa.Column("reviewer_entity_id", sa.String(length=36), nullable=False),
        sa.Column("contribution_id", sa.String(length=36), nullable=True),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("value_dec", sa.Float(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("tag1", sa.String(length=64), nullable=True),
        sa.Column("tag2", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["agent_entity_id"], ["entities.id"]),
        sa.ForeignKeyConstraint(["reviewer_entity_id"], ["entities.id"]),
        sa.ForeignKeyConstraint(["contribution_id"], ["contribution_events.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "agent_entity_id",
            "reviewer_entity_id",
            "contribution_id",
            name="uq_agent_feedback_pair_contribution",
        ),
    )
    op.create_index("ix_agent_feedback_agent_entity_id", "agent_feedback", ["agent_entity_id"])
    op.create_index("ix_agent_feedback_reviewer_entity_id", "agent_feedback", ["reviewer_entity_id"])


def downgrade() -> None:
    op.drop_index("ix_agent_feedback_reviewer_entity_id", table_name="agent_feedback")
    op.drop_index("ix_agent_feedback_agent_entity_id", table_name="agent_feedback")
    op.drop_table("agent_feedback")
