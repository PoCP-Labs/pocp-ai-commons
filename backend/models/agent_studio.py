"""Agent Studio — self-evolving Meta Agent orchestration records."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base
from db_types import JsonDocument, pocp_enum


class StudioMissionKind(str, enum.Enum):
    learn = "learn"
    grow = "grow"
    transform = "transform"
    improve = "improve"
    evolve = "evolve"


class StudioMissionStatus(str, enum.Enum):
    draft = "draft"
    active = "active"
    reviewing = "reviewing"
    completed = "completed"
    archived = "archived"


class StudioHandoffStatus(str, enum.Enum):
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"
    blocked = "blocked"


class StudioOutcomeKind(str, enum.Enum):
    test = "test"
    acceptance = "acceptance"
    review = "review"
    metric = "metric"
    human_feedback = "human_feedback"


class StudioOutcomeResult(str, enum.Enum):
    pass_ = "pass"
    fail = "fail"
    partial = "partial"


class StudioProposalKind(str, enum.Enum):
    capability_add = "capability_add"
    prompt_refine = "prompt_refine"
    config_tune = "config_tune"
    workflow_update = "workflow_update"
    skill_sync = "skill_sync"


class StudioProposalStatus(str, enum.Enum):
    draft = "draft"
    pending_review = "pending_review"
    approved = "approved"
    rejected = "rejected"
    applied = "applied"


class StudioMemoryKind(str, enum.Enum):
    episodic = "episodic"
    semantic = "semantic"
    capability = "capability"
    lesson = "lesson"


class StudioMemoryScope(str, enum.Enum):
    agent = "agent"
    studio = "studio"


class AgentStudioMission(Base):
    """Top-level self-* cycle (learn / grow / transform / improve)."""

    __tablename__ = "agent_studio_missions"
    __table_args__ = (Index("ix_agent_studio_missions_status", "status"),)

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    kind: Mapped[StudioMissionKind] = mapped_column(
        pocp_enum(StudioMissionKind), default=StudioMissionKind.evolve
    )
    status: Mapped[StudioMissionStatus] = mapped_column(
        pocp_enum(StudioMissionStatus), default=StudioMissionStatus.draft
    )
    sponsor_entity_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("entities.id"))
    orchestrator_entity_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("entities.id"))
    goal_metrics: Mapped[dict | None] = mapped_column(JsonDocument, default=dict)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JsonDocument, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class AgentStudioHandoff(Base):
    """Handoff between Meta Agents within a mission."""

    __tablename__ = "agent_studio_handoffs"
    __table_args__ = (
        Index("ix_agent_studio_handoffs_mission_id", "mission_id"),
        Index("ix_agent_studio_handoffs_from_agent", "from_agent_entity_id"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    mission_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("agent_studio_missions.id"), nullable=True
    )
    from_agent_entity_id: Mapped[str] = mapped_column(String(36), ForeignKey("entities.id"))
    to_agent_entity_id: Mapped[str] = mapped_column(String(36), ForeignKey("entities.id"))
    status: Mapped[StudioHandoffStatus] = mapped_column(
        pocp_enum(StudioHandoffStatus), default=StudioHandoffStatus.pending
    )
    scope: Mapped[str | None] = mapped_column(Text)
    files_touched: Mapped[list | None] = mapped_column(JsonDocument, default=list)
    tests_run: Mapped[str | None] = mapped_column(Text)
    blockers: Mapped[str | None] = mapped_column(Text)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JsonDocument, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class AgentStudioOutcome(Base):
    """Learning signal — tests, acceptance, reviews (Observe)."""

    __tablename__ = "agent_studio_outcomes"
    __table_args__ = (
        Index("ix_agent_studio_outcomes_agent", "agent_entity_id"),
        Index("ix_agent_studio_outcomes_mission_id", "mission_id"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    mission_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("agent_studio_missions.id"), nullable=True
    )
    handoff_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("agent_studio_handoffs.id"), nullable=True
    )
    agent_entity_id: Mapped[str] = mapped_column(String(36), ForeignKey("entities.id"))
    kind: Mapped[StudioOutcomeKind] = mapped_column(pocp_enum(StudioOutcomeKind))
    result: Mapped[StudioOutcomeResult] = mapped_column(pocp_enum(StudioOutcomeResult))
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text)
    evidence: Mapped[dict | None] = mapped_column(JsonDocument, default=dict)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JsonDocument, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AgentStudioProposal(Base):
    """Self-improvement proposal derived from outcomes (Evaluate → Refine)."""

    __tablename__ = "agent_studio_proposals"
    __table_args__ = (
        Index("ix_agent_studio_proposals_agent", "agent_entity_id"),
        Index("ix_agent_studio_proposals_status", "status"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    mission_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("agent_studio_missions.id"), nullable=True
    )
    agent_entity_id: Mapped[str] = mapped_column(String(36), ForeignKey("entities.id"))
    kind: Mapped[StudioProposalKind] = mapped_column(pocp_enum(StudioProposalKind))
    status: Mapped[StudioProposalStatus] = mapped_column(
        pocp_enum(StudioProposalStatus), default=StudioProposalStatus.pending_review
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    rationale: Mapped[str | None] = mapped_column(Text)
    proposed_changes: Mapped[dict | None] = mapped_column(JsonDocument, default=dict)
    reviewer_entity_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("entities.id"))
    review_note: Mapped[str | None] = mapped_column(Text)
    source_outcome_ids: Mapped[list | None] = mapped_column(JsonDocument, default=list)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JsonDocument, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    applied_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class AgentStudioMemory(Base):
    """Durable memory vault — per Meta Agent and studio-wide (Nexus collective)."""

    __tablename__ = "agent_studio_memories"
    __table_args__ = (
        Index("ix_agent_studio_memories_agent", "agent_entity_id"),
        Index("ix_agent_studio_memories_scope", "scope"),
        Index("ix_agent_studio_memories_kind", "kind"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    scope: Mapped[StudioMemoryScope] = mapped_column(
        pocp_enum(StudioMemoryScope), default=StudioMemoryScope.agent
    )
    agent_entity_id: Mapped[str] = mapped_column(String(36), ForeignKey("entities.id"))
    kind: Mapped[StudioMemoryKind] = mapped_column(
        pocp_enum(StudioMemoryKind), default=StudioMemoryKind.episodic
    )
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    content: Mapped[str | None] = mapped_column(Text)
    source_type: Mapped[str | None] = mapped_column(String(64))
    source_id: Mapped[str | None] = mapped_column(String(36))
    tags: Mapped[list | None] = mapped_column(JsonDocument, default=list)
    importance: Mapped[float] = mapped_column(Float, default=0.5)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JsonDocument, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
