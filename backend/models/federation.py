import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from database import Base
from db_types import JsonDocument


class FederatedImport(Base):
  __tablename__ = "federated_imports"
  __table_args__ = (
      UniqueConstraint("source_node_id", "source_contribution_id", name="uq_federated_source"),
      Index("ix_federated_imports_imported_at", "imported_at"),
  )

  id: Mapped[str] = mapped_column(
      String(36), primary_key=True, default=lambda: str(uuid.uuid4())
  )
  source_node_id: Mapped[str] = mapped_column(String(128), nullable=False)
  source_contribution_id: Mapped[str] = mapped_column(String(36), nullable=False)
  primary_entity_id: Mapped[str] = mapped_column(String(36), nullable=False)
  primary_portable_id: Mapped[str] = mapped_column(String(255), nullable=False)
  task_title: Mapped[str] = mapped_column(String(255), nullable=False)
  contribution_type: Mapped[str] = mapped_column(String(64), nullable=False)
  evidence_hash: Mapped[str] = mapped_column(String(64), nullable=False)
  ledger_record_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
  trust_weight: Mapped[float] = mapped_column(Float, default=0.5)
  reputation_applied: Mapped[float] = mapped_column(Float, default=0.0)
  payload: Mapped[dict | None] = mapped_column(JsonDocument, default=dict)
  imported_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class FederationSettlement(Base):
    __tablename__ = "federation_settlements"
    __table_args__ = (
        UniqueConstraint("settlement_key", "side", name="uq_federation_settlement_side"),
        Index("ix_federation_settlements_created_at", "created_at"),
        Index("ix_federation_settlements_provider_node", "provider_node_id"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    settlement_key: Mapped[str] = mapped_column(String(64), nullable=False)
    side: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    consumer_node_id: Mapped[str] = mapped_column(String(128), nullable=False)
    provider_node_id: Mapped[str] = mapped_column(String(128), nullable=False)
    consumer_entity_id: Mapped[str] = mapped_column(String(36), nullable=False)
    provider_entity_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    receipt_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    job_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    contribution_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    capability: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    consumer_tokens: Mapped[float] = mapped_column(Float, default=0.0)
    provider_tokens: Mapped[float] = mapped_column(Float, default=0.0)
    peer_base_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    intent_payload: Mapped[dict | None] = mapped_column(JsonDocument, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    mirrored_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
