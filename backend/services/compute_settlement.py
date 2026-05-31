"""Credit compute providers when a ComputeReceipt completes (Phase β)."""

from __future__ import annotations

import os
from typing import Any

from sqlalchemy.orm import Session

from models.entity import Entity
from models.wallet import CreditTransaction, CreditType, Wallet
from services.compute_metering import provider_tokens_for_usage, settlement_block
from services.compute_reputation import grant_compute_provider_reputation
from services.ledger_chain import append_ledger_record
from services.protocol_config import get_rewards_config


def compute_provider_credits(receipt: dict[str, Any] | None = None) -> float:
    return compute_provider_tokens(receipt)


def compute_provider_tokens(receipt: dict[str, Any] | None = None) -> float:
    if receipt:
        extra = receipt.get("extra") or {}
        usage = extra.get("usage")
        execution_mode = extra.get("execution_mode") or "live_inference"
        return provider_tokens_for_usage(
            usage,
            model=receipt.get("model"),
            capability=str(receipt.get("capability") or "llm_inference"),
            execution_mode=execution_mode,
        )
    cfg = get_rewards_config().get("compute_provider") or {}
    return float(
        cfg.get(
            "ai_credits_per_receipt",
            os.getenv("POCP_COMPUTE_PROVIDER_CREDITS", "1"),
        )
    )


def settle_compute_provider(
    db: Session,
    receipt: dict[str, Any],
    *,
    consumer_entity_id: str | None = None,
) -> dict[str, Any] | None:
    """Grant AI Credits to provider Entity wallet; idempotent per receipt hash."""
    provider_entity_id = receipt.get("provider_entity_id")
    if not provider_entity_id:
        return None

    receipt_hash = (receipt.get("integrity") or {}).get("receipt_hash")
    if not receipt_hash:
        return None

    wallet = db.query(Wallet).filter(Wallet.entity_id == provider_entity_id).first()
    if wallet is None:
        return None

    existing = (
        db.query(CreditTransaction)
        .filter(
            CreditTransaction.wallet_id == wallet.id,
            CreditTransaction.reason == f"compute_provided:{receipt_hash[:16]}",
        )
        .first()
    )
    if existing:
        return {
            "settled": False,
            "reason": "already_settled",
            "provider_entity_id": provider_entity_id,
            "receipt_hash": receipt_hash,
        }

    amount = compute_provider_tokens(receipt)
    wallet.ai_credits += amount
    contribution_id = receipt.get("contribution_id")
    usage = (receipt.get("extra") or {}).get("usage")
    settlement_meta = settlement_block(usage, pocp_tokens_consumer=0, pocp_tokens_provider=amount)
    db.add(
        CreditTransaction(
            wallet_id=wallet.id,
            amount=amount,
            credit_type=CreditType.ai_credits,
            reason=f"compute_provided:{receipt_hash[:16]}",
            contribution_id=contribution_id,
        )
    )

    entity = db.get(Entity, provider_entity_id)
    append_ledger_record(
        db,
        contribution_id=contribution_id,
        event_type="compute_provided",
        payload={
            "provider_entity_id": provider_entity_id,
            "provider_name": entity.name if entity else None,
            "consumer_entity_id": consumer_entity_id or receipt.get("initiator_entity_id"),
            "capability": receipt.get("capability"),
            "adapter": receipt.get("adapter"),
            "model": receipt.get("model"),
            "credits_granted": amount,
            "pocp_tokens_granted": amount,
            "settlement": settlement_meta,
            "receipt_hash": receipt_hash,
            "job_id": receipt.get("job_id"),
            "usage": (receipt.get("extra") or {}).get("usage"),
            "execution_mode": (receipt.get("extra") or {}).get("execution_mode"),
        },
    )

    reputation = grant_compute_provider_reputation(
        db,
        receipt,
        consumer_entity_id=consumer_entity_id,
    )

    pool_deposit = None
    try:
        from services.compute_pool import maybe_deposit_surplus_from_settlement
        from services.compute_profile import get_compute_profile

        provider = db.get(Entity, provider_entity_id)
        profile = get_compute_profile(provider) if provider else None
        org_id = (profile.get("policy") or {}).get("organization_entity_id") if profile else None
        pool_deposit = maybe_deposit_surplus_from_settlement(
            db,
            org_entity_id=org_id,
            provider_entity_id=provider_entity_id,
            credits_granted=amount,
            receipt_hash=receipt_hash,
        )
    except Exception:
        pool_deposit = None

    append_ledger_record(
        db,
        contribution_id=contribution_id,
        event_type="compute_settlement",
        payload={
            "provider_entity_id": provider_entity_id,
            "consumer_entity_id": consumer_entity_id or receipt.get("initiator_entity_id"),
            "capability": receipt.get("capability"),
            "credits_granted": amount,
            "pocp_tokens_granted": amount,
            "settlement": settlement_meta,
            "reputation_granted": (reputation or {}).get("delta"),
            "reputation_category": (reputation or {}).get("category"),
            "receipt_hash": receipt_hash,
            "job_id": receipt.get("job_id"),
            "bilateral": True,
            "usage": (receipt.get("extra") or {}).get("usage"),
            "execution_mode": (receipt.get("extra") or {}).get("execution_mode"),
            "note": "Unified PoCP Token: consumer burn at execution; provider credit on receipt.",
        },
    )
    db.flush()
    return {
        "settled": True,
        "provider_entity_id": provider_entity_id,
        "credits_granted": amount,
        "pocp_tokens_granted": amount,
        "metering_mode": (usage or {}).get("metering_mode") if usage else None,
        "settlement": settlement_meta,
        "remaining_tokens": wallet.ai_credits,
        "remaining_credits": wallet.ai_credits,
        "receipt_hash": receipt_hash,
        "reputation": reputation,
        "pool_deposit": pool_deposit,
    }
