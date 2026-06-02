"""node_profiles — Capability Internet PR-05

Revision ID: n6o7p8q9r0s1
Revises: m5n6o7p8q9r0
Create Date: 2026-06-02
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "n6o7p8q9r0s1"
down_revision: Union[str, Sequence[str], None] = "m5n6o7p8q9r0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "node_profiles" in inspector.get_table_names():
        return
    op.create_table(
        "node_profiles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("entity_id", sa.String(length=36), nullable=False),
        sa.Column("node_type", sa.String(length=32), nullable=False),
        sa.Column("did", sa.String(length=128), nullable=True),
        sa.Column("public_key", sa.String(length=512), nullable=True),
        sa.Column("base_url", sa.String(length=512), nullable=True),
        sa.Column("p2p_address", sa.String(length=512), nullable=True),
        sa.Column("health_url", sa.String(length=512), nullable=True),
        sa.Column("node_mode", sa.String(length=32), nullable=False, server_default="hosted"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="registered"),
        sa.Column("protocol_version", sa.String(length=32), nullable=False, server_default="pocp-node-v0.1"),
        sa.Column("published_capabilities", sa.JSON(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("last_heartbeat_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["entity_id"], ["entities.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_node_profiles_entity_id", "node_profiles", ["entity_id"])
    op.create_index("ix_node_profiles_status", "node_profiles", ["status"])
    op.create_index("ix_node_profiles_node_type", "node_profiles", ["node_type"])


def downgrade() -> None:
    op.drop_index("ix_node_profiles_node_type", table_name="node_profiles")
    op.drop_index("ix_node_profiles_status", table_name="node_profiles")
    op.drop_index("ix_node_profiles_entity_id", table_name="node_profiles")
    op.drop_table("node_profiles")
