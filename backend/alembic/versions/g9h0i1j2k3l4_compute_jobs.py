"""compute_jobs table for distributed scheduler persistence

Revision ID: g9h0i1j2k3l4
Revises: b1c2d3e4f5a6
Create Date: 2026-05-30
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "g9h0i1j2k3l4"
down_revision: Union[str, Sequence[str], None] = "b1c2d3e4f5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "compute_jobs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("capability", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="scheduled"),
        sa.Column("initiator_entity_id", sa.String(length=36), nullable=True),
        sa.Column("contribution_id", sa.String(length=36), nullable=True),
        sa.Column("task_id", sa.String(length=36), nullable=True),
        sa.Column("constraints", sa.JSON(), nullable=True),
        sa.Column("selected_provider", sa.JSON(), nullable=True),
        sa.Column("compute_receipt", sa.JSON(), nullable=True),
        sa.Column("execution", sa.JSON(), nullable=True),
        sa.Column("settlement", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["contribution_id"], ["contribution_events.id"]),
        sa.ForeignKeyConstraint(["initiator_entity_id"], ["entities.id"]),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_compute_jobs_contribution_id", "compute_jobs", ["contribution_id"])
    op.create_index("ix_compute_jobs_initiator_id", "compute_jobs", ["initiator_entity_id"])
    op.create_index("ix_compute_jobs_status", "compute_jobs", ["status"])


def downgrade() -> None:
    op.drop_index("ix_compute_jobs_status", table_name="compute_jobs")
    op.drop_index("ix_compute_jobs_initiator_id", table_name="compute_jobs")
    op.drop_index("ix_compute_jobs_contribution_id", table_name="compute_jobs")
    op.drop_table("compute_jobs")
