"""ledger hash_algorithm column for crypto agility

Revision ID: f8a9b0c1d2e3
Revises: e6f7a8b9c0d1
Create Date: 2026-05-30
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f8a9b0c1d2e3"
down_revision: Union[str, Sequence[str], None] = "a8b9c0d1e2f3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "ledger_records",
        sa.Column("hash_algorithm", sa.String(length=32), nullable=False, server_default="sha256"),
    )


def downgrade() -> None:
    op.drop_column("ledger_records", "hash_algorithm")
