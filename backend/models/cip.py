"""PoCP Capability Internet Protocol model proposal.

Adapt this file to the existing SQLAlchemy style before runtime import.
"""

from __future__ import annotations
import enum
from datetime import datetime
from typing import Any

try:
    from sqlalchemy import JSON, DateTime, Enum, Float, String, Text
    from sqlalchemy.orm import Mapped, mapped_column
    from .base import Base
except Exception:  # pragma: no cover
    Base = object  # type: ignore

class CIPEntityType(str, enum.Enum):
    human = "human"
    agent = "agent"
    llm = "llm"
    skill = "skill"
    tool = "tool"
    dataset = "dataset"
    workflow = "workflow"
    compute_node = "compute_node"
    verifier_node = "verifier_node"
    reviewer_node = "reviewer_node"
    organization = "organization"
    community = "community"
    sponsor = "sponsor"
    protocol_treasury = "protocol_treasury"

class CIPNodeType(str, enum.Enum):
    light = "light"
    service = "service"
    compute = "compute"
    verifier = "verifier"
    reviewer = "reviewer"
    relay = "relay"
    indexer = "indexer"
    governance = "governance"
    treasury = "treasury"

if Base is not object:
    class CIPNodeProfile(Base):
        __tablename__ = "cip_node_profiles"
        id: Mapped[str] = mapped_column(String, primary_key=True)
        entity_id: Mapped[str] = mapped_column(String, index=True)
        node_type: Mapped[CIPNodeType] = mapped_column(Enum(CIPNodeType))
        public_key: Mapped[str | None] = mapped_column(Text, nullable=True)
        base_url: Mapped[str | None] = mapped_column(String, nullable=True)
        p2p_address: Mapped[str | None] = mapped_column(String, nullable=True)
        health_url: Mapped[str | None] = mapped_column(String, nullable=True)
        protocol_version: Mapped[str] = mapped_column(String, default="pocp-node-v0.1")
        status: Mapped[str] = mapped_column(String, default="registered")
        metadata_: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSON, nullable=True)
        created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
