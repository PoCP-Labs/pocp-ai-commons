"""Contribution challenge / appeal records — verification governance."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base
from db_types import JsonDocument, pocp_enum


class DisputeKind(str, enum.Enum):
    challenge = "challenge"
    appeal = "appeal"


class DisputeStatus(str, enum.Enum):
    open = "open"
    upheld = "upheld"
    dismissed = "dismissed"
    withdrawn = "withdrawn"


class ContributionDispute(Base):
    __tablename__ = "contribution_disputes"
    __table_args__ = (
        Index("ix_contribution_disputes_contribution_id", "contribution_id"),
        Index("ix_contribution_disputes_status", "status"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    contribution_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("contribution_events.id"), nullable=False
    )
    parent_dispute_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("contribution_disputes.id"), nullable=True
    )
    kind: Mapped[DisputeKind] = mapped_column(pocp_enum(DisputeKind, length=32), nullable=False)
    status: Mapped[DisputeStatus] = mapped_column(
        pocp_enum(DisputeStatus, length=32), default=DisputeStatus.open
    )
    challenger_entity_id: Mapped[str] = mapped_column(String(36), ForeignKey("entities.id"))
    reason: Mapped[str | None] = mapped_column(Text)
    evidence_hash: Mapped[str | None] = mapped_column(String(128))
    resolution_entity_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("entities.id"))
    resolution_note: Mapped[str | None] = mapped_column(Text)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JsonDocument, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    contribution: Mapped["ContributionEvent"] = relationship(
        "ContributionEvent", back_populates="disputes"
    )
