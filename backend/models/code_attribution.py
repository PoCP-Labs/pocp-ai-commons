"""Persistent code path attribution records (complements YAML registry)."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from database import Base
from db_types import JsonDocument


class AttributionSource(str, enum.Enum):
    registry = "registry"
    git_trailer = "git_trailer"
    pr_merge = "pr_merge"
    human_confirmed = "human_confirmed"
    scan_inferred = "scan_inferred"


class CodeAttributionRecord(Base):
    """One recorded attribution of a file/path to a builder at a point in time."""

    __tablename__ = "code_attribution_records"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    builder_slug: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    entity_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("entities.id"))
    path: Mapped[str] = mapped_column(String(512), nullable=False)
    lines_count: Mapped[int] = mapped_column(Integer, default=0)
    source: Mapped[AttributionSource] = mapped_column(
        String(32), default=AttributionSource.scan_inferred.value
    )
    status: Mapped[str] = mapped_column(String(32), default="inferred")
    commit_sha: Mapped[str | None] = mapped_column(String(64))
    pr_url: Mapped[str | None] = mapped_column(String(512))
    metadata_: Mapped[dict | None] = mapped_column("metadata", JsonDocument, default=dict)
    contribution_event_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("contribution_events.id")
    )
    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
