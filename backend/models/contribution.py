import enum
import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Enum, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class ContributionStatus(str, enum.Enum):
    draft = "draft"
    submitted = "submitted"
    ai_verified = "ai_verified"
    approved = "approved"
    rejected = "rejected"


class ParticipantRole(str, enum.Enum):
    creator = "creator"
    executor = "executor"
    reviewer = "reviewer"
    verifier = "verifier"
    tool_provider = "tool_provider"
    data_provider = "data_provider"
    skill_provider = "skill_provider"
    model_provider = "model_provider"
    coordinator = "coordinator"
    sponsor = "sponsor"


class ContributionEvent(Base):
    __tablename__ = "contribution_events"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    task_id: Mapped[str] = mapped_column(String(36), ForeignKey("tasks.id"))
    primary_entity_id: Mapped[str] = mapped_column(String(36), ForeignKey("entities.id"))
    contribution_type: Mapped[str] = mapped_column(String(64), default="knowledge")
    description: Mapped[str | None] = mapped_column(Text)
    evidence: Mapped[dict | None] = mapped_column(JSON, default=dict)
    status: Mapped[ContributionStatus] = mapped_column(
        Enum(ContributionStatus), default=ContributionStatus.draft
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    task: Mapped["Task"] = relationship("Task", back_populates="contributions")
    participants: Mapped[list["ContributionParticipant"]] = relationship(
        "ContributionParticipant", back_populates="contribution"
    )
    ai_verifications: Mapped[list["AiVerifierResult"]] = relationship(
        "AiVerifierResult", back_populates="contribution"
    )
    human_reviews: Mapped[list["HumanReview"]] = relationship(
        "HumanReview", back_populates="contribution"
    )


class ContributionParticipant(Base):
    __tablename__ = "contribution_participants"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    contribution_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("contribution_events.id")
    )
    entity_id: Mapped[str] = mapped_column(String(36), ForeignKey("entities.id"))
    role: Mapped[ParticipantRole] = mapped_column(Enum(ParticipantRole), nullable=False)
    weight: Mapped[float] = mapped_column(Float, default=0.0)
    evidence: Mapped[dict | None] = mapped_column(JSON, default=dict)

    contribution: Mapped["ContributionEvent"] = relationship(
        "ContributionEvent", back_populates="participants"
    )


class AiVerifierResult(Base):
    __tablename__ = "ai_verifier_results"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    contribution_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("contribution_events.id")
    )
    model_provider: Mapped[str] = mapped_column(String(64))
    score: Mapped[float] = mapped_column(Float, default=0.0)
    feedback: Mapped[str | None] = mapped_column(Text)
    passed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    contribution: Mapped["ContributionEvent"] = relationship(
        "ContributionEvent", back_populates="ai_verifications"
    )


class HumanReview(Base):
    __tablename__ = "human_reviews"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    contribution_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("contribution_events.id")
    )
    reviewer_id: Mapped[str] = mapped_column(String(36), ForeignKey("entities.id"))
    approved: Mapped[bool] = mapped_column(Boolean, default=False)
    feedback: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    contribution: Mapped["ContributionEvent"] = relationship(
        "ContributionEvent", back_populates="human_reviews"
    )
