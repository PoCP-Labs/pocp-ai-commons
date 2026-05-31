"""federation_settlements table — cross-node PoCP Token settlement v0.4

Revision ID: i1j2k3l4m5n6
Revises: h0i1j2k3l4m5
Create Date: 2026-05-31
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "i1j2k3l4m5n6"
down_revision: Union[str, Sequence[str], None] = "h0i1j2k3l4m5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "federation_settlements",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("settlement_key", sa.String(length=64), nullable=False),
        sa.Column("side", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("consumer_node_id", sa.String(length=128), nullable=False),
        sa.Column("provider_node_id", sa.String(length=128), nullable=False),
        sa.Column("consumer_entity_id", sa.String(length=36), nullable=False),
        sa.Column("provider_entity_id", sa.String(length=36), nullable=True),
        sa.Column("receipt_hash", sa.String(length=64), nullable=False),
        sa.Column("job_id", sa.String(length=36), nullable=True),
        sa.Column("contribution_id", sa.String(length=36), nullable=True),
        sa.Column("capability", sa.String(length=64), nullable=False),
        sa.Column("consumer_tokens", sa.Float(), nullable=False),
        sa.Column("provider_tokens", sa.Float(), nullable=False),
        sa.Column("peer_base_url", sa.String(length=512), nullable=True),
        sa.Column("intent_payload", sa.JSON().with_variant(postgresql.JSONB(), "postgresql"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("mirrored_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("settlement_key", "side", name="uq_federation_settlement_side"),
    )
    op.create_index(
        "ix_federation_settlements_created_at",
        "federation_settlements",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_federation_settlements_provider_node",
        "federation_settlements",
        ["provider_node_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_federation_settlements_provider_node", table_name="federation_settlements")
    op.drop_index("ix_federation_settlements_created_at", table_name="federation_settlements")
    op.drop_table("federation_settlements")
