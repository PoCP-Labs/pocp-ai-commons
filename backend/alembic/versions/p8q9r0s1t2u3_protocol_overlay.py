"""Protocol overlay persistence — events + batches (v0.2).

Revision ID: p8q9r0s1t2u3
Revises: o7p8q9r0s1t2
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "p8q9r0s1t2u3"
down_revision: Union[str, Sequence[str], None] = "o7p8q9r0s1t2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "protocol_overlay_events" in inspector.get_table_names():
        return

    op.create_table(
        "protocol_overlay_events",
        sa.Column("event_id", sa.String(length=32), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", sa.String(length=36), nullable=True),
        sa.Column("node_id", sa.String(length=128), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("payload_hash", sa.String(length=80), nullable=True),
        sa.Column("previous_event_hash", sa.String(length=80), nullable=True),
        sa.Column("event_hash", sa.String(length=80), nullable=False),
        sa.Column("event_timestamp", sa.String(length=40), nullable=True),
        sa.Column("mempool_status", sa.String(length=16), nullable=False),
        sa.Column("batch_id", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("event_id"),
    )
    op.create_index(
        "ix_protocol_overlay_events_mempool_status",
        "protocol_overlay_events",
        ["mempool_status"],
    )
    op.create_index(
        "ix_protocol_overlay_events_batch_id",
        "protocol_overlay_events",
        ["batch_id"],
    )
    op.create_index(
        "ix_protocol_overlay_events_created_at",
        "protocol_overlay_events",
        ["created_at"],
    )
    op.create_index(
        "ix_protocol_overlay_events_event_type",
        "protocol_overlay_events",
        ["event_type"],
    )

    op.create_table(
        "protocol_overlay_batches",
        sa.Column("batch_id", sa.String(length=32), nullable=False),
        sa.Column("event_count", sa.Integer(), nullable=False),
        sa.Column("event_hashes", sa.JSON(), nullable=True),
        sa.Column("event_merkle_root", sa.String(length=80), nullable=False),
        sa.Column("merkle_root_hex", sa.String(length=64), nullable=True),
        sa.Column("previous_batch_hash", sa.String(length=80), nullable=True),
        sa.Column("batch_hash", sa.String(length=80), nullable=False),
        sa.Column("created_by_node_id", sa.String(length=128), nullable=True),
        sa.Column("batch_timestamp", sa.String(length=40), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("batch_id"),
    )
    op.create_index(
        "ix_protocol_overlay_batches_created_at",
        "protocol_overlay_batches",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_table("protocol_overlay_batches")
    op.drop_table("protocol_overlay_events")
