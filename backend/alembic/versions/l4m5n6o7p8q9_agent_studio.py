"""Revision ID: l4m5n6o7p8q9
Revises: k3l4m5n6o7p8
Create Date: 2026-06-01 — Agent Studio sub-platform tables
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "l4m5n6o7p8q9"
down_revision: Union[str, Sequence[str], None] = "k3l4m5n6o7p8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "agent_studio_missions" in inspector.get_table_names():
        return

    op.create_table(
        "agent_studio_missions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("sponsor_entity_id", sa.String(length=36), nullable=True),
        sa.Column("orchestrator_entity_id", sa.String(length=36), nullable=True),
        sa.Column("goal_metrics", sa.JSON(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["orchestrator_entity_id"], ["entities.id"]),
        sa.ForeignKeyConstraint(["sponsor_entity_id"], ["entities.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_studio_missions_status", "agent_studio_missions", ["status"])

    op.create_table(
        "agent_studio_handoffs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("mission_id", sa.String(length=36), nullable=True),
        sa.Column("from_agent_entity_id", sa.String(length=36), nullable=False),
        sa.Column("to_agent_entity_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("scope", sa.Text(), nullable=True),
        sa.Column("files_touched", sa.JSON(), nullable=True),
        sa.Column("tests_run", sa.Text(), nullable=True),
        sa.Column("blockers", sa.Text(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["from_agent_entity_id"], ["entities.id"]),
        sa.ForeignKeyConstraint(["mission_id"], ["agent_studio_missions.id"]),
        sa.ForeignKeyConstraint(["to_agent_entity_id"], ["entities.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_studio_handoffs_mission_id", "agent_studio_handoffs", ["mission_id"])
    op.create_index(
        "ix_agent_studio_handoffs_from_agent", "agent_studio_handoffs", ["from_agent_entity_id"]
    )

    op.create_table(
        "agent_studio_outcomes",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("mission_id", sa.String(length=36), nullable=True),
        sa.Column("handoff_id", sa.String(length=36), nullable=True),
        sa.Column("agent_entity_id", sa.String(length=36), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("result", sa.String(length=32), nullable=False),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("evidence", sa.JSON(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["agent_entity_id"], ["entities.id"]),
        sa.ForeignKeyConstraint(["handoff_id"], ["agent_studio_handoffs.id"]),
        sa.ForeignKeyConstraint(["mission_id"], ["agent_studio_missions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_studio_outcomes_agent", "agent_studio_outcomes", ["agent_entity_id"])
    op.create_index(
        "ix_agent_studio_outcomes_mission_id", "agent_studio_outcomes", ["mission_id"]
    )

    op.create_table(
        "agent_studio_proposals",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("mission_id", sa.String(length=36), nullable=True),
        sa.Column("agent_entity_id", sa.String(length=36), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("proposed_changes", sa.JSON(), nullable=True),
        sa.Column("reviewer_entity_id", sa.String(length=36), nullable=True),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column("source_outcome_ids", sa.JSON(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("applied_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["agent_entity_id"], ["entities.id"]),
        sa.ForeignKeyConstraint(["mission_id"], ["agent_studio_missions.id"]),
        sa.ForeignKeyConstraint(["reviewer_entity_id"], ["entities.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_studio_proposals_agent", "agent_studio_proposals", ["agent_entity_id"])
    op.create_index("ix_agent_studio_proposals_status", "agent_studio_proposals", ["status"])


def downgrade() -> None:
    op.drop_table("agent_studio_proposals")
    op.drop_table("agent_studio_outcomes")
    op.drop_table("agent_studio_handoffs")
    op.drop_table("agent_studio_missions")
