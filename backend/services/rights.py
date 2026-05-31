"""BC/CP rights mechanics for PoCP v0.1.

BC v0.1 is represented by the existing AI Credits wallet balance and can be
spent on protocol AI services. CP v0.1 is non-spendable contribution proof: it
can be minted for approved human contribution, but this module intentionally
does not provide a CP spend path.
"""

from dataclasses import asdict, dataclass
from typing import Literal

from sqlalchemy.orm import Session

from models.contribution import ContributionEvent, ContributionParticipant, ParticipantRole
from models.entity import Entity, EntityType
from models.wallet import CreditTransaction, CreditType, Wallet
from services.issuance_budget import assert_issuance_allowed
from services.ledger_chain import append_ledger_record
from services.protocol_config import get_rewards_config

RightKind = Literal["bc", "cp"]

BC_VERSION = "bc_v0_1"
CP_VERSION = "cp_v0_1"


@dataclass(frozen=True)
class RightPolicy:
    kind: RightKind
    version: str
    wallet_field: str
    transaction_type: CreditType
    spendable: bool
    transferable: bool
    description: str


@dataclass(frozen=True)
class RightsGrant:
    entity_id: str
    contribution_id: str | None
    kind: RightKind
    version: str
    amount: float
    reason: str
    wallet_id: str
    spendable: bool
    transferable: bool


def rights_policy() -> dict[RightKind, RightPolicy]:
    config = get_rewards_config().get("rights", {})
    bc = config.get("bc", {})
    cp = config.get("cp", {})
    return {
        "bc": RightPolicy(
            kind="bc",
            version=str(bc.get("version", BC_VERSION)),
            wallet_field="ai_credits",
            transaction_type=CreditType.ai_credits,
            spendable=bool(bc.get("spendable", True)),
            transferable=bool(bc.get("transferable", False)),
            description=str(
                bc.get("description", "AI Credits spendable on protocol AI services")
            ),
        ),
        "cp": RightPolicy(
            kind="cp",
            version=str(cp.get("version", CP_VERSION)),
            wallet_field="cp_balance",
            transaction_type=CreditType.cp,
            spendable=bool(cp.get("spendable", False)),
            transferable=bool(cp.get("transferable", False)),
            description=str(cp.get("description", "Non-spendable contribution proof")),
        ),
    }


def get_or_create_wallet(db: Session, entity_id: str) -> Wallet:
    wallet = db.query(Wallet).filter(Wallet.entity_id == entity_id).first()
    if wallet is None:
        wallet = Wallet(entity_id=entity_id)
        db.add(wallet)
        db.flush()
    return wallet


def issue_right(
    db: Session,
    *,
    entity_id: str,
    kind: RightKind,
    amount: float,
    reason: str,
    contribution_id: str | None = None,
) -> RightsGrant:
    if amount < 0:
        raise ValueError("Rights issuance amount cannot be negative")

    if kind == "cp":
        assert_issuance_allowed(db, cp_amount=amount)
    elif kind == "bc":
        assert_issuance_allowed(db, bc_amount=amount)

    policy = rights_policy()[kind]
    wallet = get_or_create_wallet(db, entity_id)
    current_balance = float(getattr(wallet, policy.wallet_field))
    setattr(wallet, policy.wallet_field, current_balance + amount)
    db.add(
        CreditTransaction(
            wallet_id=wallet.id,
            contribution_id=contribution_id,
            amount=amount,
            credit_type=policy.transaction_type,
            reason=reason,
        )
    )
    db.flush()
    return RightsGrant(
        entity_id=entity_id,
        contribution_id=contribution_id,
        kind=kind,
        version=policy.version,
        amount=amount,
        reason=reason,
        wallet_id=wallet.id,
        spendable=policy.spendable,
        transferable=policy.transferable,
    )


def issue_registration_bc(db: Session, entity: Entity) -> Wallet | None:
    if entity.entity_type != EntityType.human:
        return None

    wallet = get_or_create_wallet(db, entity.id)
    if wallet.ai_credits > 0 or wallet.cp_balance > 0:
        return wallet

    amount = float(get_rewards_config()["registration"]["ai_credits"])
    grant = issue_right(
        db,
        entity_id=entity.id,
        kind="bc",
        amount=amount,
        reason="Registration grant",
    )
    append_ledger_record(
        db,
        contribution_id=None,
        event_type="registration_grant",
        payload={
            "entity_id": entity.id,
            "rights": [asdict(grant)],
            "ai_credits": amount,
        },
    )
    db.flush()
    return wallet


def contribution_rights_amounts(participant: ContributionParticipant) -> dict[str, float]:
    defaults = get_rewards_config()["contribution_defaults"]["human"]
    cp_base = float(defaults["cp_base"])
    bc_base = float(defaults["ai_credits_base"])
    weight = participant.weight or 0.4
    return {
        "cp": round(cp_base * weight / 0.4, 2),
        "bc": round(bc_base * weight / 0.4, 2),
    }


def entity_equal_enabled() -> bool:
    return bool(get_rewards_config().get("entity_equal", {}).get("enabled", False))


def entity_bc_amount(entity_type: EntityType, participant: ContributionParticipant) -> float | None:
    if not entity_equal_enabled():
        return None
    defaults = get_rewards_config()["contribution_defaults"]
    if entity_type == EntityType.agent and participant.role in (
        ParticipantRole.executor,
        ParticipantRole.creator,
    ):
        base = float(defaults.get("agent", {}).get("ai_credits_base", 0))
        weight = participant.weight or 0.25
        return round(base * weight / 0.25, 2) if base > 0 else None
    if entity_type == EntityType.skill and participant.role == ParticipantRole.skill_provider:
        base = float(defaults.get("skill", {}).get("ai_credits_base", 0))
        weight = participant.weight or 0.15
        return round(base * weight / 0.15, 2) if base > 0 else None
    if entity_type == EntityType.llm and participant.role in (
        ParticipantRole.model_provider,
        ParticipantRole.verifier,
        ParticipantRole.skill_provider,
    ):
        base = float(defaults.get("llm", {}).get("ai_credits_base", 0))
        weight = participant.weight or 0.1
        return round(base * weight / 0.1, 2) if base > 0 else None
    return None


def issue_entity_bc_grant(
    db: Session,
    *,
    contribution: ContributionEvent,
    participant: ContributionParticipant,
    entity: Entity,
) -> RightsGrant | None:
    amount = entity_bc_amount(entity.entity_type, participant)
    if amount is None or amount <= 0:
        return None
    return issue_right(
        db,
        entity_id=entity.id,
        contribution_id=contribution.id,
        kind="bc",
        amount=amount,
        reason=f"Entity-equal AI Credits ({entity.entity_type.value}/{participant.role.value})",
    )


def issue_contribution_rights(
    db: Session,
    *,
    contribution: ContributionEvent,
    participant: ContributionParticipant,
    entity: Entity,
) -> list[RightsGrant]:
    if entity.entity_type != EntityType.human:
        return []
    if participant.role not in (ParticipantRole.creator, ParticipantRole.executor):
        return []

    amounts = contribution_rights_amounts(participant)
    role = participant.role.value
    return [
        issue_right(
            db,
            entity_id=entity.id,
            contribution_id=contribution.id,
            kind="cp",
            amount=amounts["cp"],
            reason=f"Contribution proof ({role})",
        ),
        issue_right(
            db,
            entity_id=entity.id,
            contribution_id=contribution.id,
            kind="bc",
            amount=amounts["bc"],
            reason=f"Contribution reward ({role})",
        ),
    ]


def assert_spendable(kind: RightKind) -> None:
    policy = rights_policy()[kind]
    if not policy.spendable:
        raise ValueError(f"{policy.version} is not spendable")
