"""entity_capabilities table — Neural Commons v0.4

Revision ID: h0i1j2k3l4m5
Revises: g9h0i1j2k3l4
Create Date: 2026-05-29
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "h0i1j2k3l4m5"
down_revision: Union[str, Sequence[str], None] = "g9h0i1j2k3l4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "entity_capabilities" in inspector.get_table_names():
        return
    op.create_table(
        "entity_capabilities",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("entity_id", sa.String(length=36), nullable=False),
        sa.Column("capability_type", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("unit", sa.String(length=64), nullable=False),
        sa.Column("price_model", sa.String(length=32), nullable=False, server_default="fixed"),
        sa.Column("base_price", sa.Float(), nullable=False, server_default="0"),
        sa.Column("accepted_units", sa.JSON(), nullable=True),
        sa.Column("verification_method", sa.String(length=64), nullable=False, server_default="human_review"),
        sa.Column("availability", sa.String(length=32), nullable=False, server_default="available"),
        sa.Column("reputation_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("risk_level", sa.String(length=16), nullable=False, server_default="low"),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["entity_id"], ["entities.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_entity_capabilities_entity_id", "entity_capabilities", ["entity_id"])
    op.create_index("ix_entity_capabilities_capability_type", "entity_capabilities", ["capability_type"])
    op.create_index("ix_entity_capabilities_availability", "entity_capabilities", ["availability"])


def downgrade() -> None:
    op.drop_index("ix_entity_capabilities_availability", table_name="entity_capabilities")
    op.drop_index("ix_entity_capabilities_capability_type", table_name="entity_capabilities")
    op.drop_index("ix_entity_capabilities_entity_id", table_name="entity_capabilities")
    op.drop_table("entity_capabilities")
