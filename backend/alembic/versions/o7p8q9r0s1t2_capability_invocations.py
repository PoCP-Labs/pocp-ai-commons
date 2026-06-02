"""capability_invocations — Capability Internet PR-07

Revision ID: o7p8q9r0s1t2
Revises: n6o7p8q9r0s1
Create Date: 2026-06-02
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "o7p8q9r0s1t2"
down_revision: Union[str, Sequence[str], None] = "n6o7p8q9r0s1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "capability_invocations" in inspector.get_table_names():
        return
    op.create_table(
        "capability_invocations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("task_id", sa.String(length=36), nullable=True),
        sa.Column("caller_entity_id", sa.String(length=36), nullable=False),
        sa.Column("callee_entity_id", sa.String(length=36), nullable=False),
        sa.Column("capability_id", sa.String(length=64), nullable=False),
        sa.Column("input_hash", sa.String(length=128), nullable=False),
        sa.Column("output_hash", sa.String(length=128), nullable=True),
        sa.Column("cost_unit", sa.String(length=16), nullable=True),
        sa.Column("cost_amount", sa.Float(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="created"),
        sa.Column("trace_id", sa.String(length=36), nullable=True),
        sa.Column("exchange_id", sa.String(length=64), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["caller_entity_id"], ["entities.id"]),
        sa.ForeignKeyConstraint(["callee_entity_id"], ["entities.id"]),
        sa.ForeignKeyConstraint(["capability_id"], ["entity_capabilities.id"]),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"]),
        sa.ForeignKeyConstraint(["trace_id"], ["invocation_traces.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_capability_invocations_caller", "capability_invocations", ["caller_entity_id"])
    op.create_index("ix_capability_invocations_callee", "capability_invocations", ["callee_entity_id"])
    op.create_index("ix_capability_invocations_capability_id", "capability_invocations", ["capability_id"])
    op.create_index("ix_capability_invocations_status", "capability_invocations", ["status"])
    op.create_index("ix_capability_invocations_trace_id", "capability_invocations", ["trace_id"])


def downgrade() -> None:
    op.drop_index("ix_capability_invocations_trace_id", table_name="capability_invocations")
    op.drop_index("ix_capability_invocations_status", table_name="capability_invocations")
    op.drop_index("ix_capability_invocations_capability_id", table_name="capability_invocations")
    op.drop_index("ix_capability_invocations_callee", table_name="capability_invocations")
    op.drop_index("ix_capability_invocations_caller", table_name="capability_invocations")
    op.drop_table("capability_invocations")
