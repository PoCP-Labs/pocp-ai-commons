"""Persisted Protocol Event overlay — mempool events and sealed batches (v0.2)."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from database import Base
from db_types import JsonDocument, pocp_enum


class OverlayEventMempoolStatus(str, enum.Enum):
    pending = "pending"
    sealed = "sealed"


class ProtocolOverlayEvent(Base):
    __tablename__ = "protocol_overlay_events"
    __table_args__ = (
        Index("ix_protocol_overlay_events_mempool_status", "mempool_status"),
        Index("ix_protocol_overlay_events_batch_id", "batch_id"),
        Index("ix_protocol_overlay_events_created_at", "created_at"),
        Index("ix_protocol_overlay_events_event_type", "event_type"),
    )

    event_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    node_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    payload: Mapped[dict | None] = mapped_column(JsonDocument, default=dict)
    payload_hash: Mapped[str | None] = mapped_column(String(80), nullable=True)
    previous_event_hash: Mapped[str | None] = mapped_column(String(80), nullable=True)
    event_hash: Mapped[str] = mapped_column(String(80), nullable=False)
    event_timestamp: Mapped[str | None] = mapped_column(String(40), nullable=True)
    mempool_status: Mapped[OverlayEventMempoolStatus] = mapped_column(
        pocp_enum(OverlayEventMempoolStatus),
        default=OverlayEventMempoolStatus.pending,
    )
    batch_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ProtocolOverlayBatch(Base):
    __tablename__ = "protocol_overlay_batches"
    __table_args__ = (Index("ix_protocol_overlay_batches_created_at", "created_at"),)

    batch_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    event_count: Mapped[int] = mapped_column(Integer, default=0)
    event_hashes: Mapped[list | None] = mapped_column(JsonDocument, default=list)
    event_merkle_root: Mapped[str] = mapped_column(String(80), nullable=False)
    merkle_root_hex: Mapped[str | None] = mapped_column(String(64), nullable=True)
    previous_batch_hash: Mapped[str | None] = mapped_column(String(80), nullable=True)
    batch_hash: Mapped[str] = mapped_column(String(80), nullable=False)
    created_by_node_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    batch_timestamp: Mapped[str | None] = mapped_column(String(40), nullable=True)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JsonDocument, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
