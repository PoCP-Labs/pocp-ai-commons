"""add AI usage records table — closes the genesis loop.

Revision ID: 003_ai_usage
Revises: 002_add_indexes
Create Date: 2026-05-30
"""

from alembic import op
import sqlalchemy as sa

revision = "003_ai_usage"
down_revision = "002_add_indexes"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "ai_usage_records",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("entity_id", sa.String(36), sa.ForeignKey("entities.id"), nullable=False),
        sa.Column("model_provider", sa.String(64), nullable=False),
        sa.Column("prompt", sa.Text, nullable=False),
        sa.Column("response", sa.Text),
        sa.Column("credits_deducted", sa.Float, nullable=False),
        sa.Column("status", sa.String(16), server_default="completed"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_ai_usage_entity", "ai_usage_records", ["entity_id"])
    op.create_index("ix_ai_usage_created", "ai_usage_records", ["created_at"])


def downgrade():
    op.drop_index("ix_ai_usage_created", "ai_usage_records")
    op.drop_index("ix_ai_usage_entity", "ai_usage_records")
    op.drop_table("ai_usage_records")
