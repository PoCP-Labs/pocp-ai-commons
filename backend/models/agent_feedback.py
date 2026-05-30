import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class AgentFeedback(Base):
    """Off-chain agent reputation signals (ERC-8004 Reputation Registry pattern)."""

    __tablename__ = "agent_feedback"
    __table_args__ = (
        UniqueConstraint(
            "agent_entity_id",
            "reviewer_entity_id",
            "contribution_id",
            name="uq_agent_feedback_pair_contribution",
        ),
        Index("ix_agent_feedback_agent_entity_id", "agent_entity_id"),
        Index("ix_agent_feedback_reviewer_entity_id", "reviewer_entity_id"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    agent_entity_id: Mapped[str] = mapped_column(String(36), ForeignKey("entities.id"))
    reviewer_entity_id: Mapped[str] = mapped_column(String(36), ForeignKey("entities.id"))
    contribution_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("contribution_events.id"), nullable=True
    )
    score: Mapped[float] = mapped_column(Float, default=0.0)
    value_dec: Mapped[float] = mapped_column(Float, default=0.0)
    comment: Mapped[str | None] = mapped_column(Text)
    tag1: Mapped[str | None] = mapped_column(String(64))
    tag2: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    agent: Mapped["Entity"] = relationship("Entity", foreign_keys=[agent_entity_id])
    reviewer: Mapped["Entity"] = relationship("Entity", foreign_keys=[reviewer_entity_id])
