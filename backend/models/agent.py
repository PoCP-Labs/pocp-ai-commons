import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base
from db_types import JsonDocument


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    entity_id: Mapped[str] = mapped_column(String(36), ForeignKey("entities.id"), unique=True)
    config: Mapped[dict | None] = mapped_column(JsonDocument, default=dict)
    maintainer_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("entities.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    entity: Mapped["Entity"] = relationship("Entity", back_populates="agent", foreign_keys=[entity_id])
