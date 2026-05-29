import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    entity_id: Mapped[str] = mapped_column(String(36), ForeignKey("entities.id"), unique=True)
    version: Mapped[str] = mapped_column(String(32), default="1.0.0")
    prompt_template: Mapped[str | None] = mapped_column(Text)
    maintainer_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("entities.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    entity: Mapped["Entity"] = relationship("Entity", back_populates="skill", foreign_keys=[entity_id])
