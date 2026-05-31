"""Persistent records of external OSS inspirations and their PoCP contributions."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from database import Base
from db_types import JsonDocument


class InspirationRecordSource(str, enum.Enum):
    registry = "registry"
    human_confirmed = "human_confirmed"
    sync = "sync"


class ExternalInspirationRecord(Base):
    """One documented contribution borrowed from an external project."""

    __tablename__ = "external_inspiration_records"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    inspiration_slug: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    contribution_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    entity_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("entities.id"))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    relationship: Mapped[str] = mapped_column(String(32), default="pattern_borrowed")
    status: Mapped[str] = mapped_column(String(32), default="recorded")
    pocp_modules: Mapped[list | None] = mapped_column(JsonDocument, default=list)
    api_paths: Mapped[list | None] = mapped_column(JsonDocument, default=list)
    proof_layers: Mapped[list | None] = mapped_column(JsonDocument, default=list)
    integration_section: Mapped[int | None] = mapped_column(nullable=True)
    source: Mapped[str] = mapped_column(
        String(32), default=InspirationRecordSource.registry.value
    )
    metadata_: Mapped[dict | None] = mapped_column("metadata", JsonDocument, default=dict)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
