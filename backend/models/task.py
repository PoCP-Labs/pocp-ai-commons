import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base
from db_types import pocp_enum


class TaskStatus(str, enum.Enum):
    open = "open"
    in_progress = "in_progress"
    completed = "completed"
    closed = "closed"


class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = (Index("ix_tasks_status", "status"),)

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    sponsor_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("entities.id"))
    status: Mapped[TaskStatus] = mapped_column(pocp_enum(TaskStatus), default=TaskStatus.open)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    contributions: Mapped[list["ContributionEvent"]] = relationship(
        "ContributionEvent", back_populates="task"
    )
