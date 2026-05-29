import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base
from db_types import pocp_enum


class CreditType(str, enum.Enum):
    cp = "cp"
    ai_credits = "ai_credits"


class Wallet(Base):
    __tablename__ = "wallets"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    entity_id: Mapped[str] = mapped_column(String(36), ForeignKey("entities.id"), unique=True)
    cp_balance: Mapped[float] = mapped_column(Float, default=0.0)
    ai_credits: Mapped[float] = mapped_column(Float, default=0.0)

    entity: Mapped["Entity"] = relationship("Entity", back_populates="wallet")
    transactions: Mapped[list["CreditTransaction"]] = relationship(
        "CreditTransaction", back_populates="wallet"
    )


class CreditTransaction(Base):
    __tablename__ = "credit_transactions"
    __table_args__ = (Index("ix_credit_transactions_wallet_id", "wallet_id"),)

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    wallet_id: Mapped[str] = mapped_column(String(36), ForeignKey("wallets.id"))
    contribution_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("contribution_events.id")
    )
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    credit_type: Mapped[CreditType] = mapped_column(pocp_enum(CreditType), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    wallet: Mapped["Wallet"] = relationship("Wallet", back_populates="transactions")


class ReputationScore(Base):
    __tablename__ = "reputation_scores"
    __table_args__ = (Index("ix_reputation_scores_entity_id", "entity_id"),)

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    entity_id: Mapped[str] = mapped_column(String(36), ForeignKey("entities.id"))
    score: Mapped[float] = mapped_column(Float, default=0.0)
    category: Mapped[str] = mapped_column(String(64), default="general")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    entity: Mapped["Entity"] = relationship("Entity", back_populates="reputation")
