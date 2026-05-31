"""merge invocation metadata and ledger hash algorithm heads

Revision ID: b1c2d3e4f5a6
Revises: a8b9c0d1e2f3, f8a9b0c1d2e3
Create Date: 2026-05-31
"""

from typing import Sequence, Union

revision: str = "b1c2d3e4f5a6"
down_revision: Union[str, Sequence[str], None] = ("a8b9c0d1e2f3", "f8a9b0c1d2e3")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
