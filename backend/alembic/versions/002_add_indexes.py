"""add performance indexes for frequently queried columns.

Revision ID: 002_add_indexes
Revises: 001_initial
Create Date: 2026-05-30
"""

from alembic import op

revision = "002_add_indexes"
down_revision = "001_initial"
branch_labels = None
depends_on = None


def upgrade():
    # Entities — lookups by type and status
    op.create_index("ix_entities_type", "entities", ["entity_type"])
    op.create_index("ix_entities_status", "entities", ["status"])
    op.create_index("ix_entities_owner", "entities", ["owner_id"])
    op.create_index("ix_entities_creator", "entities", ["creator_id"])

    # Contributions — frequent filtering by status and task
    op.create_index("ix_contributions_status", "contribution_events", ["status"])
    op.create_index("ix_contributions_task", "contribution_events", ["task_id"])
    op.create_index("ix_contributions_primary", "contribution_events", ["primary_entity_id"])
    op.create_index("ix_contributions_created", "contribution_events", ["created_at"])

    # Participants — lookups by entity and contribution
    op.create_index("ix_participants_contribution", "contribution_participants", ["contribution_id"])
    op.create_index("ix_participants_entity", "contribution_participants", ["entity_id"])

    # AI verifier — lookups by contribution
    op.create_index("ix_ai_verifier_contribution", "ai_verifier_results", ["contribution_id"])

    # Human reviews — lookups by contribution and reviewer
    op.create_index("ix_human_reviews_contribution", "human_reviews", ["contribution_id"])
    op.create_index("ix_human_reviews_reviewer", "human_reviews", ["reviewer_id"])

    # Wallets — lookups by entity
    op.create_index("ix_wallets_entity", "wallets", ["entity_id"], unique=True)

    # Credit transactions — lookups by wallet and contribution
    op.create_index("ix_credit_tx_wallet", "credit_transactions", ["wallet_id"])
    op.create_index("ix_credit_tx_contribution", "credit_transactions", ["contribution_id"])

    # Reputation — lookups by entity
    op.create_index("ix_reputation_entity", "reputation_scores", ["entity_id"])

    # Ledger — lookups by event type
    op.create_index("ix_ledger_event_type", "ledger_records", ["event_type"])

    # Tasks — lookups by status and sponsor
    op.create_index("ix_tasks_status", "tasks", ["status"])
    op.create_index("ix_tasks_sponsor", "tasks", ["sponsor_id"])

    # Invocations — lookups by initiator
    op.create_index("ix_invocation_initiator", "invocation_traces", ["initiator_id"])
    op.create_index("ix_invocation_contribution", "invocation_traces", ["contribution_id"])

    # Invocation steps — lookups by trace
    op.create_index("ix_invocation_steps_trace", "invocation_steps", ["trace_id"])

    # Skills, agents, orgs — lookups by entity
    op.create_index("ix_skills_entity", "skills", ["entity_id"], unique=True)
    op.create_index("ix_agents_entity", "agents", ["entity_id"], unique=True)
    op.create_index("ix_orgs_entity", "organizations", ["entity_id"], unique=True)


def downgrade():
    op.drop_index("ix_orgs_entity", "organizations")
    op.drop_index("ix_agents_entity", "agents")
    op.drop_index("ix_skills_entity", "skills")
    op.drop_index("ix_invocation_steps_trace", "invocation_steps")
    op.drop_index("ix_invocation_contribution", "invocation_traces")
    op.drop_index("ix_invocation_initiator", "invocation_traces")
    op.drop_index("ix_tasks_sponsor", "tasks")
    op.drop_index("ix_tasks_status", "tasks")
    op.drop_index("ix_ledger_event_type", "ledger_records")
    op.drop_index("ix_reputation_entity", "reputation_scores")
    op.drop_index("ix_credit_tx_contribution", "credit_transactions")
    op.drop_index("ix_credit_tx_wallet", "credit_transactions")
    op.drop_index("ix_wallets_entity", "wallets")
    op.drop_index("ix_human_reviews_reviewer", "human_reviews")
    op.drop_index("ix_human_reviews_contribution", "human_reviews")
    op.drop_index("ix_ai_verifier_contribution", "ai_verifier_results")
    op.drop_index("ix_participants_entity", "contribution_participants")
    op.drop_index("ix_participants_contribution", "contribution_participants")
    op.drop_index("ix_contributions_created", "contribution_events")
    op.drop_index("ix_contributions_primary", "contribution_events")
    op.drop_index("ix_contributions_task", "contribution_events")
    op.drop_index("ix_contributions_status", "contribution_events")
    op.drop_index("ix_entities_creator", "entities")
    op.drop_index("ix_entities_owner", "entities")
    op.drop_index("ix_entities_status", "entities")
    op.drop_index("ix_entities_type", "entities")
