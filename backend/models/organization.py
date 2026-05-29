import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base
from db_types import JsonDocument


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    entity_id: Mapped[str] = mapped_column(String(36), ForeignKey("entities.id"), unique=True)
    org_type: Mapped[str] = mapped_column(String(64), default="community")
    governance_proxy_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("entities.id")
    )
    config: Mapped[dict | None] = mapped_column(JsonDocument, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    entity: Mapped["Entity"] = relationship(
        "Entity", back_populates="organization", foreign_keys=[entity_id]
    )
