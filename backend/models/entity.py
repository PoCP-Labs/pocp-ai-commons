import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class EntityType(str, enum.Enum):
    human = "human"
    agent = "agent"
    skill = "skill"
    llm = "llm"
    tool = "tool"
    dataset = "dataset"
    workflow = "workflow"
    organization = "organization"
    community = "community"


class EntityStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"
    pending = "pending"


class Entity(Base):
    __tablename__ = "entities"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    entity_type: Mapped[EntityType] = mapped_column(Enum(EntityType), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    owner_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("entities.id"))
    creator_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("entities.id"))
    status: Mapped[EntityStatus] = mapped_column(
        Enum(EntityStatus), default=EntityStatus.active
    )
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    skill: Mapped["Skill | None"] = relationship(
        "Skill", back_populates="entity", uselist=False, foreign_keys="Skill.entity_id"
    )
    agent: Mapped["Agent | None"] = relationship(
        "Agent", back_populates="entity", uselist=False, foreign_keys="Agent.entity_id"
    )
    wallet: Mapped["Wallet | None"] = relationship("Wallet", back_populates="entity", uselist=False)
    reputation: Mapped[list["ReputationScore"]] = relationship(
        "ReputationScore", back_populates="entity"
    )
    organization: Mapped["Organization | None"] = relationship(
        "Organization",
        back_populates="entity",
        uselist=False,
        foreign_keys="Organization.entity_id",
    )
