"""Node profiles — Entity binding to network connectivity (Capability Internet PR-05)."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base
from db_types import JsonDocument, pocp_enum


class NodeType(str, enum.Enum):
    light = "light"
    service = "service"
    compute = "compute"
    verifier = "verifier"
    reviewer = "reviewer"
    relay = "relay"
    indexer = "indexer"
    governance = "governance"
    treasury = "treasury"


class NodeStatus(str, enum.Enum):
    registered = "registered"
    active = "active"
    offline = "offline"
    suspended = "suspended"


class NodeMode(str, enum.Enum):
    direct_public = "direct_public"
    reverse_proxy = "reverse_proxy"
    relay = "relay"
    hosted = "hosted"
    offline_light = "offline_light"


class NodeProfileRecord(Base):
    """Persistent NodeProfile — one primary profile per Entity (idempotent upsert by entity_id)."""

    __tablename__ = "node_profiles"
    __table_args__ = (
        Index("ix_node_profiles_entity_id", "entity_id"),
        Index("ix_node_profiles_status", "status"),
        Index("ix_node_profiles_node_type", "node_type"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    entity_id: Mapped[str] = mapped_column(String(36), ForeignKey("entities.id"), nullable=False)
    node_type: Mapped[NodeType] = mapped_column(pocp_enum(NodeType, length=32), nullable=False)
    did: Mapped[str | None] = mapped_column(String(128))
    public_key: Mapped[str | None] = mapped_column(String(512))
    base_url: Mapped[str | None] = mapped_column(String(512))
    p2p_address: Mapped[str | None] = mapped_column(String(512))
    health_url: Mapped[str | None] = mapped_column(String(512))
    node_mode: Mapped[NodeMode] = mapped_column(
        pocp_enum(NodeMode, length=32), default=NodeMode.hosted
    )
    status: Mapped[NodeStatus] = mapped_column(
        pocp_enum(NodeStatus, length=32), default=NodeStatus.registered
    )
    protocol_version: Mapped[str] = mapped_column(String(32), default="pocp-node-v0.1")
    published_capabilities: Mapped[list | None] = mapped_column(
        JsonDocument, default=list
    )
    metadata_: Mapped[dict | None] = mapped_column("metadata", JsonDocument, default=dict)
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    entity: Mapped["Entity"] = relationship("Entity", foreign_keys=[entity_id])
