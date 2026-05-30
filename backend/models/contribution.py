"""Contribution Event — the minimal protocol object by which PoCP recognizes contribution.

A Contribution Event is not merely a submitted artifact or reported action.
It is a responsibility-bearing claim that identifiable entities created
task-relevant value through collaboration.

See PROTOCOL-SPEC-v0.2.md §2.4 for the full protocol definition.
"""

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

    # Protocol rule: approved requires prior ai_verified
    # Protocol rule: AI verification never sets approved directly
    # Protocol rule: rejected is terminal (but can re-submit as new event)


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

    # --- Protocol Properties (v0.2) ---

    @property
    def has_evidence(self) -> bool:
        """Principle 4: Evidence Bundle. A claim without evidence is not a Contribution Event."""
        return bool(self.evidence)

    @property
    def has_participants(self) -> bool:
        """Must have at least one attributed participant."""
        return len(self.participants) > 0

    @property
    def has_ai_verification(self) -> bool:
        """Principle 5: Verification Required. At least one AI advisory review."""
        return len(self.ai_verifications) > 0

    @property
    def has_human_approval(self) -> bool:
        """Principle 6: Accountability. At least one human review with approved=True."""
        return any(r.approved for r in self.human_reviews)

    @property
    def has_rejection(self) -> bool:
        """Has been rejected by a human reviewer."""
        return any(not r.approved for r in self.human_reviews)

    @property
    def is_established(self) -> bool:
        """A Contribution Event is formally established only when:
        1. The claim is submitted
        2. Evidence is attached
        3. AI advisory verification is recorded
        4. Accountable human review is completed
        5. Rights conversion has been executed (status=approved implies this)
        6. Ledger Memory has been written (checked at service layer)

        This property checks conditions 1-5. Condition 6 is verified by
        checking for a corresponding ledger_record at the service layer.
        """
        return (
            self.status == ContributionStatus.approved
            and self.has_evidence
            and self.has_participants
            and self.has_ai_verification
            and self.has_human_approval
        )

    def validate_for_submission(self) -> list[str]:
        """Validate that the contribution can be submitted.

        Returns a list of error messages. Empty list = valid.
        """
        errors = []
        if not self.task_id:
            errors.append("Contribution must be attached to a task (Principle 1: Task Attachment)")
        if not self.primary_entity_id:
            errors.append("Contribution must have a primary responsible entity (Principle 2: Claim)")
        if not self.description:
            errors.append("Contribution must have a description of the value claim")
        if not self.has_evidence:
            errors.append("Contribution must have evidence attached (Principle 4: Evidence Bundle)")
        if not self.has_participants:
            errors.append("Contribution must have at least one attributed participant")
        return errors


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
