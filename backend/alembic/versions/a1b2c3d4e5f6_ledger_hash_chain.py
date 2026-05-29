"""ledger hash chain columns

Revision ID: a1b2c3d4e5f6
Revises: 72f32ab86a41
Create Date: 2026-05-29 22:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "72f32ab86a41"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("ledger_records", sa.Column("prev_hash", sa.String(length=64), nullable=True))
    op.add_column("ledger_records", sa.Column("record_hash", sa.String(length=64), nullable=True))
    op.create_index("ix_ledger_records_record_hash", "ledger_records", ["record_hash"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_ledger_records_record_hash", table_name="ledger_records")
    op.drop_column("ledger_records", "record_hash")
    op.drop_column("ledger_records", "prev_hash")
