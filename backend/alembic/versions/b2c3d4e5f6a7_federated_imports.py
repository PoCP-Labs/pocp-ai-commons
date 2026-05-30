"""federated imports table

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-05-29 23:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "federated_imports",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("source_node_id", sa.String(length=128), nullable=False),
        sa.Column("source_contribution_id", sa.String(length=36), nullable=False),
        sa.Column("primary_entity_id", sa.String(length=36), nullable=False),
        sa.Column("primary_portable_id", sa.String(length=255), nullable=False),
        sa.Column("task_title", sa.String(length=255), nullable=False),
        sa.Column("contribution_type", sa.String(length=64), nullable=False),
        sa.Column("evidence_hash", sa.String(length=64), nullable=False),
        sa.Column("ledger_record_hash", sa.String(length=64), nullable=True),
        sa.Column("trust_weight", sa.Float(), nullable=False),
        sa.Column("reputation_applied", sa.Float(), nullable=False),
        sa.Column("payload", sa.JSON().with_variant(postgresql.JSONB(), "postgresql"), nullable=True),
        sa.Column("imported_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_node_id", "source_contribution_id", name="uq_federated_source"),
    )
    op.create_index("ix_federated_imports_imported_at", "federated_imports", ["imported_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_federated_imports_imported_at", table_name="federated_imports")
    op.drop_table("federated_imports")
