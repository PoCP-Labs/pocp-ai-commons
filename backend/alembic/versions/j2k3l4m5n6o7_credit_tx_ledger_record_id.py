"""credit_transactions.ledger_record_id — exchange spine FK

Revision ID: j2k3l4m5n6o7
Revises: i1j2k3l4m5n6
Create Date: 2026-05-29
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "j2k3l4m5n6o7"
down_revision: Union[str, Sequence[str], None] = "i1j2k3l4m5n6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("credit_transactions", schema=None) as batch_op:
        batch_op.add_column(sa.Column("ledger_record_id", sa.String(length=36), nullable=True))
        batch_op.create_index(
            "ix_credit_transactions_ledger_record_id",
            ["ledger_record_id"],
            unique=False,
        )
        batch_op.create_foreign_key(
            "fk_credit_transactions_ledger_record_id",
            "ledger_records",
            ["ledger_record_id"],
            ["id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("credit_transactions", schema=None) as batch_op:
        batch_op.drop_constraint("fk_credit_transactions_ledger_record_id", type_="foreignkey")
        batch_op.drop_index("ix_credit_transactions_ledger_record_id")
        batch_op.drop_column("ledger_record_id")
