import enum
import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class InvocationStatus(str, enum.Enum):
    started = "started"
    completed = "completed"
    failed = "failed"


class InvocationTrace(Base):
    """Records Human → Agent → Skill → LLM call chains."""

    __tablename__ = "invocation_traces"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    initiator_id: Mapped[str] = mapped_column(String(36), ForeignKey("entities.id"))
    task_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("tasks.id"))
    contribution_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("contribution_events.id")
    )
    model_provider: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[InvocationStatus] = mapped_column(
        Enum(InvocationStatus), default=InvocationStatus.completed
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    steps: Mapped[list["InvocationStep"]] = relationship(
        "InvocationStep", back_populates="trace", order_by="InvocationStep.step_order"
    )


class InvocationStep(Base):
    __tablename__ = "invocation_steps"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    trace_id: Mapped[str] = mapped_column(String(36), ForeignKey("invocation_traces.id"))
    step_order: Mapped[int] = mapped_column(Integer, nullable=False)
    source_entity_id: Mapped[str] = mapped_column(String(36), ForeignKey("entities.id"))
    target_entity_id: Mapped[str] = mapped_column(String(36), ForeignKey("entities.id"))
    action: Mapped[str] = mapped_column(String(64), nullable=False)

    trace: Mapped["InvocationTrace"] = relationship("InvocationTrace", back_populates="steps")
