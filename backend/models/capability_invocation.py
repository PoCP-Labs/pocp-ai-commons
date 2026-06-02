"""Capability-bound invocation ledger — PR-07."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from database import Base
from db_types import JsonDocument, pocp_enum


class CapabilityInvocationStatus(str, enum.Enum):
    created = "created"
    accepted = "accepted"
    running = "running"
    completed = "completed"
    proof_submitted = "proof_submitted"
    verified = "verified"
    settled = "settled"
    failed = "failed"
    disputed = "disputed"


# Valid forward transitions (state machine).
CAPABILITY_INVOCATION_TRANSITIONS: dict[CapabilityInvocationStatus, frozenset[CapabilityInvocationStatus]] = {
    CapabilityInvocationStatus.created: frozenset(
        {
            CapabilityInvocationStatus.accepted,
            CapabilityInvocationStatus.running,
            CapabilityInvocationStatus.completed,
            CapabilityInvocationStatus.failed,
        }
    ),
    CapabilityInvocationStatus.accepted: frozenset(
        {CapabilityInvocationStatus.running, CapabilityInvocationStatus.failed}
    ),
    CapabilityInvocationStatus.running: frozenset(
        {CapabilityInvocationStatus.completed, CapabilityInvocationStatus.failed}
    ),
    CapabilityInvocationStatus.completed: frozenset(
        {
            CapabilityInvocationStatus.proof_submitted,
            CapabilityInvocationStatus.verified,
            CapabilityInvocationStatus.settled,
            CapabilityInvocationStatus.failed,
        }
    ),
    CapabilityInvocationStatus.proof_submitted: frozenset(
        {CapabilityInvocationStatus.verified, CapabilityInvocationStatus.settled, CapabilityInvocationStatus.disputed}
    ),
    CapabilityInvocationStatus.verified: frozenset(
        {CapabilityInvocationStatus.settled, CapabilityInvocationStatus.disputed}
    ),
    CapabilityInvocationStatus.settled: frozenset(),
    CapabilityInvocationStatus.failed: frozenset(),
    CapabilityInvocationStatus.disputed: frozenset(
        {CapabilityInvocationStatus.verified, CapabilityInvocationStatus.settled}
    ),
}


class CapabilityInvocationRecord(Base):
    """Flat capability invocation — caller/callee/capability_id with cost and hashes."""

    __tablename__ = "capability_invocations"
    __table_args__ = (
        Index("ix_capability_invocations_caller", "caller_entity_id"),
        Index("ix_capability_invocations_callee", "callee_entity_id"),
        Index("ix_capability_invocations_capability_id", "capability_id"),
        Index("ix_capability_invocations_status", "status"),
        Index("ix_capability_invocations_trace_id", "trace_id"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    task_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("tasks.id"))
    caller_entity_id: Mapped[str] = mapped_column(String(36), ForeignKey("entities.id"), nullable=False)
    callee_entity_id: Mapped[str] = mapped_column(String(36), ForeignKey("entities.id"), nullable=False)
    capability_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("entity_capabilities.id"), nullable=False
    )
    input_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    output_hash: Mapped[str | None] = mapped_column(String(128))
    cost_unit: Mapped[str | None] = mapped_column(String(16))
    cost_amount: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[CapabilityInvocationStatus] = mapped_column(
        pocp_enum(CapabilityInvocationStatus, length=32),
        default=CapabilityInvocationStatus.created,
    )
    trace_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("invocation_traces.id")
    )
    exchange_id: Mapped[str | None] = mapped_column(String(64))
    metadata_: Mapped[dict | None] = mapped_column("metadata", JsonDocument, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
