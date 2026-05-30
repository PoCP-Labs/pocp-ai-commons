"""Merge duplicate human entities that share the same display name."""

from __future__ import annotations

import logging

from sqlalchemy import update
from sqlalchemy.orm import Session

from genesis import RAIN_ID
from models.agent import Agent
from models.ai_usage import AIUsageLog
from models.code_attribution import CodeAttributionRecord
from models.contribution import ContributionEvent, ContributionParticipant, HumanReview
from models.entity import Entity, EntityType
from models.invocation import InvocationStep, InvocationTrace
from models.organization import Organization
from models.skill import Skill
from models.task import Task
from models.user_account import UserAccount
from models.wallet import CreditTransaction, ReputationScore, Wallet
from services.rights import get_or_create_wallet

logger = logging.getLogger(__name__)

# (model, column_name) pairs that reference entities.id
_ENTITY_FK_COLUMNS: list[tuple[type, str]] = [
    (ContributionEvent, "primary_entity_id"),
    (HumanReview, "reviewer_id"),
    (InvocationTrace, "initiator_id"),
    (InvocationStep, "source_entity_id"),
    (InvocationStep, "target_entity_id"),
    (Agent, "maintainer_id"),
    (Skill, "maintainer_id"),
    (Task, "sponsor_id"),
    (Organization, "governance_proxy_id"),
    (AIUsageLog, "entity_id"),
    (CodeAttributionRecord, "entity_id"),
    (ReputationScore, "entity_id"),
]


def _repoint_column(db: Session, model: type, column: str, from_id: str, to_id: str) -> int:
    col = getattr(model, column)
    result = db.execute(update(model).where(col == from_id).values({column: to_id}))
    return result.rowcount or 0


def _repoint_entity_self_refs(db: Session, from_id: str, to_id: str) -> int:
    count = 0
    for field in ("owner_id", "creator_id"):
        col = getattr(Entity, field)
        result = db.execute(update(Entity).where(col == from_id).values({field: to_id}))
        count += result.rowcount or 0
    return count


def _repoint_participants(db: Session, from_id: str, to_id: str) -> None:
    rows = db.query(ContributionParticipant).filter(ContributionParticipant.entity_id == from_id).all()
    for row in rows:
        conflict = (
            db.query(ContributionParticipant)
            .filter(
                ContributionParticipant.contribution_id == row.contribution_id,
                ContributionParticipant.entity_id == to_id,
                ContributionParticipant.role == row.role,
            )
            .first()
        )
        if conflict is not None:
            conflict.weight = float(conflict.weight) + float(row.weight)
            db.delete(row)
        else:
            row.entity_id = to_id


def _merge_wallets(db: Session, from_id: str, to_id: str) -> None:
    src = db.query(Wallet).filter(Wallet.entity_id == from_id).first()
    if src is None:
        return
    dst = get_or_create_wallet(db, to_id)
    dst.cp_balance = float(dst.cp_balance) + float(src.cp_balance)
    dst.ai_credits = float(dst.ai_credits) + float(src.ai_credits)
    db.execute(
        update(CreditTransaction).where(CreditTransaction.wallet_id == src.id).values(wallet_id=dst.id)
    )
    db.execute(update(AIUsageLog).where(AIUsageLog.wallet_id == src.id).values(wallet_id=dst.id))
    db.delete(src)


def _merge_reputation(db: Session, from_id: str, to_id: str) -> None:
    for src in db.query(ReputationScore).filter(ReputationScore.entity_id == from_id).all():
        dst = (
            db.query(ReputationScore)
            .filter(
                ReputationScore.entity_id == to_id,
                ReputationScore.category == src.category,
            )
            .first()
        )
        if dst is None:
            src.entity_id = to_id
        else:
            dst.score = float(dst.score) + float(src.score)
            db.delete(src)


def _repoint_user_accounts(db: Session, from_id: str, to_id: str) -> None:
    for account in db.query(UserAccount).filter(UserAccount.entity_id == from_id).all():
        account.entity_id = to_id


def merge_entity_into(db: Session, from_id: str, to_id: str) -> None:
    """Move all references from from_id to to_id, then delete from_id."""
    if from_id == to_id:
        return
    if db.get(Entity, from_id) is None:
        return
    if db.get(Entity, to_id) is None:
        raise ValueError(f"Canonical entity {to_id} does not exist")

    _repoint_participants(db, from_id, to_id)
    for model, column in _ENTITY_FK_COLUMNS:
        _repoint_column(db, model, column, from_id, to_id)
    _repoint_entity_self_refs(db, from_id, to_id)
    _repoint_user_accounts(db, from_id, to_id)
    _merge_reputation(db, from_id, to_id)
    _merge_wallets(db, from_id, to_id)

    duplicate = db.get(Entity, from_id)
    if duplicate is not None:
        db.delete(duplicate)


def merge_rain_duplicates(db: Session) -> int:
    """Merge extra Rain humans into pocp-entity-rain (genesis canonical id)."""
    canonical = db.get(Entity, RAIN_ID)
    if canonical is None:
        return 0

    duplicates = (
        db.query(Entity)
        .filter(
            Entity.name == "Rain",
            Entity.entity_type == EntityType.human,
            Entity.id != RAIN_ID,
        )
        .all()
    )
    if not duplicates:
        return 0

    for dup in duplicates:
        logger.info("Merging duplicate Rain %s into %s", dup.id, RAIN_ID)
        merge_entity_into(db, dup.id, RAIN_ID)

    if not canonical.description:
        canonical.description = "Founder and protocol initiator of PoCP AI Commons"

    return len(duplicates)
