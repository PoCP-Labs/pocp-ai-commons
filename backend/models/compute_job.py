"""Persisted distributed compute jobs (scheduler → receipt → settlement)."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String
from db_types import JsonDocument
from sqlalchemy.orm import Mapped, mapped_column

from database import Base
from db_types import pocp_enum


class ComputeJobStatus(str, enum.Enum):
    scheduled = "scheduled"
    completed = "completed"
    failed = "failed"


class ComputeJobRecord(Base):
    __tablename__ = "compute_jobs"
    __table_args__ = (
        Index("ix_compute_jobs_contribution_id", "contribution_id"),
        Index("ix_compute_jobs_initiator_id", "initiator_entity_id"),
        Index("ix_compute_jobs_status", "status"),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: f"compute-job-{uuid.uuid4().hex[:12]}",
    )
    capability: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[ComputeJobStatus] = mapped_column(
        pocp_enum(ComputeJobStatus),
        default=ComputeJobStatus.scheduled,
    )
    initiator_entity_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("entities.id"), nullable=True
    )
    contribution_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("contribution_events.id"), nullable=True
    )
    task_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("tasks.id"), nullable=True)
    constraints_: Mapped[dict | None] = mapped_column("constraints", JsonDocument, nullable=True)
    selected_provider: Mapped[dict | None] = mapped_column(JsonDocument, nullable=True)
    compute_receipt: Mapped[dict | None] = mapped_column(JsonDocument, nullable=True)
    execution_: Mapped[dict | None] = mapped_column("execution", JsonDocument, nullable=True)
    settlement: Mapped[dict | None] = mapped_column(JsonDocument, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
