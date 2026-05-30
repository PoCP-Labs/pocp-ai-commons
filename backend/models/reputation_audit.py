import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from database import Base
from db_types import JsonDocument


class ReputationAuditEntry(Base):
    """Meritocrab-style audit trail for reputation changes."""

    __tablename__ = "reputation_audit_entries"
    __table_args__ = (
        Index("ix_reputation_audit_entity_id", "entity_id"),
        Index("ix_reputation_audit_source", "source"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    entity_id: Mapped[str] = mapped_column(String(36), ForeignKey("entities.id"))
    category: Mapped[str] = mapped_column(String(64))
    delta: Mapped[float] = mapped_column(Float, default=0.0)
    balance_after: Mapped[float] = mapped_column(Float, default=0.0)
    source: Mapped[str] = mapped_column(String(64))
    reason: Mapped[str | None] = mapped_column(Text)
    reference_id: Mapped[str | None] = mapped_column(String(128))
    actor_entity_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("entities.id"))
    payload: Mapped[dict | None] = mapped_column(JsonDocument, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
