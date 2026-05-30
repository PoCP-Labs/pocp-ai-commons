"""initial migration — create all tables from current models.

Revision ID: 001_initial
Revises:
Create Date: 2026-05-30
"""

from alembic import op
import sqlalchemy as sa

revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # entities
    op.create_table(
        "entities",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("entity_type", sa.Enum("human", "agent", "skill", "llm", "tool", "dataset", "workflow", "organization", "community", name="entitytype"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("owner_id", sa.String(36), sa.ForeignKey("entities.id")),
        sa.Column("creator_id", sa.String(36), sa.ForeignKey("entities.id")),
        sa.Column("status", sa.Enum("active", "inactive", "pending", name="entitystatus"), server_default="active"),
        sa.Column("metadata", sa.JSON, server_default="{}"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # wallets
    op.create_table(
        "wallets",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("entity_id", sa.String(36), sa.ForeignKey("entities.id"), unique=True),
        sa.Column("cp_balance", sa.Float, server_default="0.0"),
        sa.Column("ai_credits", sa.Float, server_default="0.0"),
    )

    # credit transactions
    op.create_table(
        "credit_transactions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("wallet_id", sa.String(36), sa.ForeignKey("wallets.id"), nullable=False),
        sa.Column("contribution_id", sa.String(36), sa.ForeignKey("contribution_events.id")),
        sa.Column("amount", sa.Float, nullable=False),
        sa.Column("credit_type", sa.Enum("cp", "ai_credits", name="credittype"), nullable=False),
        sa.Column("reason", sa.String(255)),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    # reputation scores
    op.create_table(
        "reputation_scores",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("entity_id", sa.String(36), sa.ForeignKey("entities.id"), nullable=False),
        sa.Column("score", sa.Float, server_default="0.0"),
        sa.Column("category", sa.String(64), server_default="general"),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # tasks
    op.create_table(
        "tasks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("sponsor_id", sa.String(36), sa.ForeignKey("entities.id")),
        sa.Column("status", sa.Enum("open", "in_progress", "completed", "closed", name="taskstatus"), server_default="open"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    # contribution events
    op.create_table(
        "contribution_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("task_id", sa.String(36), sa.ForeignKey("tasks.id"), nullable=False),
        sa.Column("primary_entity_id", sa.String(36), sa.ForeignKey("entities.id"), nullable=False),
        sa.Column("contribution_type", sa.String(64), server_default="knowledge"),
        sa.Column("description", sa.Text),
        sa.Column("evidence", sa.JSON, server_default="{}"),
        sa.Column("status", sa.Enum("draft", "submitted", "ai_verified", "approved", "rejected", name="contributionstatus"), server_default="draft"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    # contribution participants
    op.create_table(
        "contribution_participants",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("contribution_id", sa.String(36), sa.ForeignKey("contribution_events.id"), nullable=False),
        sa.Column("entity_id", sa.String(36), sa.ForeignKey("entities.id"), nullable=False),
        sa.Column("role", sa.Enum("creator", "executor", "reviewer", "verifier", "tool_provider", "data_provider", "skill_provider", "model_provider", "coordinator", "sponsor", name="participantrole"), nullable=False),
        sa.Column("weight", sa.Float, server_default="0.0"),
        sa.Column("evidence", sa.JSON, server_default="{}"),
    )

    # AI verifier results
    op.create_table(
        "ai_verifier_results",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("contribution_id", sa.String(36), sa.ForeignKey("contribution_events.id"), nullable=False),
        sa.Column("model_provider", sa.String(64), nullable=False),
        sa.Column("score", sa.Float, server_default="0.0"),
        sa.Column("feedback", sa.Text),
        sa.Column("passed", sa.Boolean, server_default="false"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    # human reviews
    op.create_table(
        "human_reviews",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("contribution_id", sa.String(36), sa.ForeignKey("contribution_events.id"), nullable=False),
        sa.Column("reviewer_id", sa.String(36), sa.ForeignKey("entities.id"), nullable=False),
        sa.Column("approved", sa.Boolean, server_default="false"),
        sa.Column("feedback", sa.Text),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    # ledger records
    op.create_table(
        "ledger_records",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("contribution_id", sa.String(36), sa.ForeignKey("contribution_events.id")),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("payload", sa.JSON, server_default="{}"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    # agents
    op.create_table(
        "agents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("entity_id", sa.String(36), sa.ForeignKey("entities.id"), unique=True),
        sa.Column("config", sa.JSON, server_default="{}"),
        sa.Column("maintainer_id", sa.String(36), sa.ForeignKey("entities.id")),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    # skills
    op.create_table(
        "skills",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("entity_id", sa.String(36), sa.ForeignKey("entities.id"), unique=True),
        sa.Column("version", sa.String(32), server_default="1.0.0"),
        sa.Column("prompt_template", sa.Text),
        sa.Column("maintainer_id", sa.String(36), sa.ForeignKey("entities.id")),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    # organizations
    op.create_table(
        "organizations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("entity_id", sa.String(36), sa.ForeignKey("entities.id"), unique=True),
        sa.Column("org_type", sa.String(64), server_default="community"),
        sa.Column("governance_proxy_id", sa.String(36), sa.ForeignKey("entities.id")),
        sa.Column("config", sa.JSON, server_default="{}"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    # invocation traces
    op.create_table(
        "invocation_traces",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("initiator_id", sa.String(36), sa.ForeignKey("entities.id"), nullable=False),
        sa.Column("task_id", sa.String(36), sa.ForeignKey("tasks.id")),
        sa.Column("contribution_id", sa.String(36), sa.ForeignKey("contribution_events.id")),
        sa.Column("model_provider", sa.String(64)),
        sa.Column("status", sa.Enum("started", "completed", "failed", name="invocationstatus"), server_default="completed"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    # invocation steps
    op.create_table(
        "invocation_steps",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("trace_id", sa.String(36), sa.ForeignKey("invocation_traces.id"), nullable=False),
        sa.Column("step_order", sa.Integer, nullable=False),
        sa.Column("source_entity_id", sa.String(36), sa.ForeignKey("entities.id"), nullable=False),
        sa.Column("target_entity_id", sa.String(36), sa.ForeignKey("entities.id"), nullable=False),
        sa.Column("action", sa.String(64), nullable=False),
    )


def downgrade():
    op.drop_table("invocation_steps")
    op.drop_table("invocation_traces")
    op.drop_table("organizations")
    op.drop_table("skills")
    op.drop_table("agents")
    op.drop_table("ledger_records")
    op.drop_table("human_reviews")
    op.drop_table("ai_verifier_results")
    op.drop_table("contribution_participants")
    op.drop_table("contribution_events")
    op.drop_table("tasks")
    op.drop_table("reputation_scores")
    op.drop_table("credit_transactions")
    op.drop_table("wallets")
    op.drop_table("entities")
