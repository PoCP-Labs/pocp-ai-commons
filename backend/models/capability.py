"""Capability registry records — Neural Commons v0.4."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base
from db_types import JsonDocument, pocp_enum


class CapabilityType(str, enum.Enum):
    coding = "coding"
    reasoning = "reasoning"
    review = "review"
    gpu_inference = "gpu_inference"
    gpu_training = "gpu_training"
    tool_call = "tool_call"
    verification = "verification"
    governance = "governance"
    general = "general"


class CapabilityUnit(str, enum.Enum):
    skill_invocation = "skill_invocation"
    agent_run = "agent_run"
    llm_token = "llm_token"
    gpu_second = "gpu_second"
    task = "task"


class PriceModel(str, enum.Enum):
    fixed = "fixed"
    dynamic = "dynamic"
    auction = "auction"
    sponsored = "sponsored"


class CapabilityAvailability(str, enum.Enum):
    available = "available"
    limited = "limited"
    offline = "offline"


class EntityCapability(Base):
    """Registered capability offered by an Entity (schema v0.3)."""

    __tablename__ = "entity_capabilities"
    __table_args__ = (
        Index("ix_entity_capabilities_entity_id", "entity_id"),
        Index("ix_entity_capabilities_capability_type", "capability_type"),
        Index("ix_entity_capabilities_availability", "availability"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    entity_id: Mapped[str] = mapped_column(String(36), ForeignKey("entities.id"), nullable=False)
    capability_type: Mapped[CapabilityType] = mapped_column(
        pocp_enum(CapabilityType, length=64), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    unit: Mapped[CapabilityUnit] = mapped_column(pocp_enum(CapabilityUnit, length=64), nullable=False)
    price_model: Mapped[PriceModel] = mapped_column(
        pocp_enum(PriceModel, length=32), default=PriceModel.fixed
    )
    base_price: Mapped[float] = mapped_column(Float, default=0.0)
    accepted_units: Mapped[list | None] = mapped_column(JsonDocument, default=lambda: ["AIC"])
    verification_method: Mapped[str] = mapped_column(String(64), default="human_review")
    availability: Mapped[CapabilityAvailability] = mapped_column(
        pocp_enum(CapabilityAvailability, length=32), default=CapabilityAvailability.available
    )
    reputation_score: Mapped[float] = mapped_column(Float, default=0.0)
    risk_level: Mapped[str] = mapped_column(String(16), default="low")
    metadata_: Mapped[dict | None] = mapped_column("metadata", JsonDocument, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    entity: Mapped["Entity"] = relationship("Entity", foreign_keys=[entity_id])
