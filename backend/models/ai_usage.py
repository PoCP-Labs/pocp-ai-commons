"""AI Credits consumption — the missing half of the genesis loop.

Genesis cycle:
  Contribution → Verification → CP → AI Credits → AI USE → More Contribution

This module closes the loop: entities can SPEND their AI Credits
to access AI capabilities (chat, code, analysis, etc.).

AI Credits are NOT currency. They are network rights earned through contribution.
"""

import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class AIUsageRecord(Base):
    """Record of AI capability usage by an entity.

    Each usage deducts AI Credits and creates a ledger entry.
    This is how the genesis loop closes: earned credits → used capability.
    """

    __tablename__ = "ai_usage_records"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    entity_id: Mapped[str] = mapped_column(String(36), ForeignKey("entities.id"), nullable=False)
    model_provider: Mapped[str] = mapped_column(String(64), nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    response: Mapped[str | None] = mapped_column(Text)
    credits_deducted: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="completed")  # completed, failed, insufficient
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
