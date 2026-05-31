"""Bilateral PoCP Token settlement — consumer debit + provider credit in one flow."""

from __future__ import annotations

import hashlib
import json
import os
from typing import Any

from sqlalchemy.orm import Session

from models.entity import Entity, EntityStatus, EntityType
from models.wallet import CreditTransaction, CreditType, Wallet
from services.compute_metering import (
    consumer_tokens_for_usage,
    orchestration_split_shares,
    provider_tokens_for_usage,
    settlement_block,
    _round_tokens,
)
from services.compute_reputation import grant_compute_provider_reputation
from services.exchange_spine import emit_exchange_settled, infer_exchange_kind
from services.ledger_chain import append_ledger_record
from services.market_pricing import resolve_intel_listing_price, resolve_rate_overrides
from services.protocol_config import get_rewards_config


def _wallet(db: Session, entity_id: str) -> Wallet | None:
    return db.query(Wallet).filter(Wallet.entity_id == entity_id).first()


def _tx_exists(db: Session, wallet_id: int, reason: str) -> bool:
    return (
        db.query(CreditTransaction)
        .filter(
            CreditTransaction.wallet_id == wallet_id,
            CreditTransaction.reason == reason,
        )
        .first()
        is not None
    )


def _resolve_protocol_treasury_id(db: Session) -> str | None:
    env_id = os.getenv("POCP_PROTOCOL_TREASURY_ID")
    if env_id:
        return env_id
    row = (
        db.query(Entity)
        .filter(Entity.entity_type == EntityType.protocol_treasury, Entity.status == EntityStatus.active)
        .first()
    )
    return row.id if row else None


def _credit_wallet(
    db: Session,
    *,
    entity_id: str,
    amount: float,
    reason: str,
    contribution_id: str | None,
    created_txs: list[CreditTransaction] | None = None,
) -> Wallet | None:
    if amount <= 0:
        return None
    wallet = _wallet(db, entity_id)
    if wallet is None:
        return None
    wallet.ai_credits += amount
    tx = CreditTransaction(
        wallet_id=wallet.id,
        amount=amount,
        credit_type=CreditType.ai_credits,
        reason=reason,
        contribution_id=contribution_id,
    )
    db.add(tx)
    if created_txs is not None:
        created_txs.append(tx)
    return wallet


def _rate_overrides(db: Session | None, receipt: dict[str, Any]) -> dict[str, float]:
    if db is None:
        return {}
    return resolve_rate_overrides(
        db,
        provider_entity_id=receipt.get("provider_entity_id"),
        capability=str(receipt.get("capability") or "llm_inference"),
        model=receipt.get("model"),
    )


def compute_provider_tokens(receipt: dict[str, Any] | None = None, *, db: Session | None = None) -> float:
    if receipt:
        extra = receipt.get("extra") or {}
        usage = extra.get("usage")
        execution_mode = extra.get("execution_mode") or "live_inference"
        overrides = _rate_overrides(db, receipt)
        return provider_tokens_for_usage(
            usage,
            model=receipt.get("model"),
            capability=str(receipt.get("capability") or "llm_inference"),
            execution_mode=execution_mode,
            rate_overrides=overrides or None,
        )
    cfg = get_rewards_config().get("compute_provider") or {}
    return float(
        cfg.get(
            "ai_credits_per_receipt",
            os.getenv("POCP_COMPUTE_PROVIDER_CREDITS", "1"),
        )
    )


def compute_provider_credits(receipt: dict[str, Any] | None = None, *, db: Session | None = None) -> float:
    return compute_provider_tokens(receipt, db=db)


def compute_consumer_tokens(receipt: dict[str, Any] | None = None, *, db: Session | None = None) -> float:
    if not receipt:
        return float(os.getenv("SKILL_EXECUTE_COST", "5"))
    extra = receipt.get("extra") or {}
    usage = extra.get("usage")
    execution_mode = extra.get("execution_mode") or "live_inference"
    overrides = _rate_overrides(db, receipt)
    return consumer_tokens_for_usage(
        usage,
        model=receipt.get("model"),
        capability=str(receipt.get("capability") or "llm_inference"),
        execution_mode=execution_mode,
        rate_overrides=overrides or None,
    )


def settle_bilateral(
    db: Session,
    receipt: dict[str, Any],
    *,
    consumer_entity_id: str | None = None,
    skill_entity_id: str | None = None,
) -> dict[str, Any] | None:
    """Debit consumer and credit provider atomically; idempotent per receipt hash.

    When ``skill_entity_id`` is set (Skill chain execution), applies v0.4 multi-party
    split: one consumer debit, credits for LLM compute provider, Skill orchestrator,
    and optional protocol treasury fee.
    """
    provider_entity_id = receipt.get("provider_entity_id")
    if not provider_entity_id:
        return None

    receipt_hash = (receipt.get("integrity") or {}).get("receipt_hash")
    if not receipt_hash:
        return None

    from services.compute_receipt import verify_compute_receipt, verify_provider_receipt_signature

    if not verify_compute_receipt(receipt):
        return {
            "settled": False,
            "reason": "invalid_receipt",
            "receipt_hash": receipt_hash,
        }
    require_sig = os.getenv("POCP_REQUIRE_RECEIPT_SIGNATURE", "false").lower() == "true"
    has_sig = bool((receipt.get("integrity") or {}).get("provider_signature"))
    if require_sig and not verify_provider_receipt_signature(receipt):
        return {
            "settled": False,
            "reason": "unsigned_or_invalid_receipt_signature",
            "receipt_hash": receipt_hash,
        }
    if has_sig and not verify_provider_receipt_signature(receipt):
        return {
            "settled": False,
            "reason": "invalid_receipt_signature",
            "receipt_hash": receipt_hash,
        }

    consumer_id = consumer_entity_id or receipt.get("initiator_entity_id")
    if not consumer_id:
        return None

    provider_wallet = _wallet(db, provider_entity_id)
    if provider_wallet is None:
        return None

    prov_reason = f"compute_provided:{receipt_hash[:16]}"
    if _tx_exists(db, provider_wallet.id, prov_reason):
        return {
            "settled": False,
            "reason": "already_settled",
            "provider_entity_id": provider_entity_id,
            "receipt_hash": receipt_hash,
        }

    raw_provider_amount = compute_provider_tokens(receipt, db=db)
    consumer_amount = compute_consumer_tokens(receipt, db=db)
    if consumer_id == provider_entity_id:
        consumer_amount = 0.0

    split_shares: dict[str, float] | None = None
    skill_share = 0.0
    protocol_fee = 0.0
    burn_amount = 0.0
    provider_amount = raw_provider_amount
    if skill_entity_id and consumer_amount > 0:
        split_shares = orchestration_split_shares(consumer_amount, raw_provider_amount)
        provider_amount = split_shares["compute_share"]
        skill_share = split_shares["skill_share"]
        protocol_fee = split_shares["protocol_fee"]
        burn_amount = split_shares["burn"]

    contribution_id = receipt.get("contribution_id")
    usage = (receipt.get("extra") or {}).get("usage")
    consumer_debited = 0.0
    settlement_kind = (
        "skill_orchestration_split" if skill_entity_id and split_shares else "compute_bilateral"
    )
    exchange_txs: list[CreditTransaction] = []

    consumer_wallet = _wallet(db, consumer_id)
    if consumer_amount > 0:
        if consumer_wallet is None:
            return {
                "settled": False,
                "reason": "consumer_wallet_missing",
                "consumer_entity_id": consumer_id,
                "receipt_hash": receipt_hash,
            }
        from services.anti_abuse import check_daily_ai_burn_limit

        check_daily_ai_burn_limit(db, consumer_id, consumer_amount)
        if consumer_wallet.ai_credits < consumer_amount:
            return {
                "settled": False,
                "reason": "insufficient_consumer_balance",
                "consumer_entity_id": consumer_id,
                "required_tokens": consumer_amount,
                "available_tokens": consumer_wallet.ai_credits,
                "receipt_hash": receipt_hash,
            }
        consumer_wallet.ai_credits -= consumer_amount
        consumer_debited = consumer_amount
        burn_payload: dict[str, Any] = {
            "entity_id": consumer_id,
            "wallet_id": consumer_wallet.id,
            "credits_spent": consumer_amount,
            "pocp_tokens_spent": consumer_amount,
            "remaining_credits": consumer_wallet.ai_credits,
            "remaining_tokens": consumer_wallet.ai_credits,
            "receipt_hash": receipt_hash,
            "capability": receipt.get("capability"),
            "settlement_kind": settlement_kind,
        }
        if split_shares:
            burn_payload["split"] = {
                **split_shares,
                "skill_entity_id": skill_entity_id,
                "compute_provider_entity_id": provider_entity_id,
            }
        consumer_tx = CreditTransaction(
            wallet_id=consumer_wallet.id,
            amount=-consumer_amount,
            credit_type=CreditType.ai_credits,
            reason=f"compute_consumed:{receipt_hash[:16]}",
            contribution_id=contribution_id,
        )
        db.add(consumer_tx)
        exchange_txs.append(consumer_tx)
        append_ledger_record(
            db,
            contribution_id=contribution_id,
            event_type="ai_credits_burned",
            payload=burn_payload,
        )

    settlement_meta = settlement_block(
        usage,
        pocp_tokens_consumer=consumer_debited,
        pocp_tokens_provider=provider_amount,
        split=(
            {
                **split_shares,
                "skill_entity_id": skill_entity_id,
                "compute_provider_entity_id": provider_entity_id,
                "protocol_treasury_entity_id": None,
            }
            if split_shares
            else None
        ),
    )

    provider_wallet.ai_credits += provider_amount
    provider_tx = CreditTransaction(
        wallet_id=provider_wallet.id,
        amount=provider_amount,
        credit_type=CreditType.ai_credits,
        reason=prov_reason,
        contribution_id=contribution_id,
    )
    db.add(provider_tx)
    exchange_txs.append(provider_tx)

    skill_credited = 0.0
    protocol_credited = 0.0
    treasury_entity_id: str | None = None
    if split_shares and skill_entity_id and skill_share > 0:
        skill_reason = f"skill_orchestration:{receipt_hash[:16]}"
        skill_wallet = _credit_wallet(
            db,
            entity_id=skill_entity_id,
            amount=skill_share,
            reason=skill_reason,
            contribution_id=contribution_id,
            created_txs=exchange_txs,
        )
        if skill_wallet:
            skill_credited = skill_share
            skill_entity = db.get(Entity, skill_entity_id)
            append_ledger_record(
                db,
                contribution_id=contribution_id,
                event_type="intel_provided",
                payload={
                    "provider_entity_id": skill_entity_id,
                    "provider_name": skill_entity.name if skill_entity else None,
                    "consumer_entity_id": consumer_id,
                    "service": "skill_orchestration",
                    "credits_granted": skill_share,
                    "pocp_tokens_granted": skill_share,
                    "consumer_tokens": consumer_debited,
                    "settlement": settlement_meta,
                    "receipt_hash": receipt_hash,
                    "split_role": "skill_orchestration",
                },
            )

    if split_shares and protocol_fee > 0:
        treasury_entity_id = _resolve_protocol_treasury_id(db)
        if treasury_entity_id:
            treasury_reason = f"protocol_fee:{receipt_hash[:16]}"
            treasury_wallet = _credit_wallet(
                db,
                entity_id=treasury_entity_id,
                amount=protocol_fee,
                reason=treasury_reason,
                contribution_id=contribution_id,
                created_txs=exchange_txs,
            )
            if treasury_wallet:
                protocol_credited = protocol_fee
                if settlement_meta.get("split") is not None:
                    settlement_meta["split"]["protocol_treasury_entity_id"] = treasury_entity_id
                append_ledger_record(
                    db,
                    contribution_id=contribution_id,
                    event_type="protocol_fee_collected",
                    payload={
                        "treasury_entity_id": treasury_entity_id,
                        "consumer_entity_id": consumer_id,
                        "protocol_fee": protocol_fee,
                        "pocp_tokens_granted": protocol_fee,
                        "receipt_hash": receipt_hash,
                        "settlement": settlement_meta,
                    },
                )
        else:
            burn_amount = _round_tokens(burn_amount + protocol_fee)
            protocol_fee = 0.0

    if split_shares and burn_amount > 0:
        append_ledger_record(
            db,
            contribution_id=contribution_id,
            event_type="protocol_tokens_burned",
            payload={
                "consumer_entity_id": consumer_id,
                "burn_amount": burn_amount,
                "receipt_hash": receipt_hash,
                "settlement_kind": settlement_kind,
            },
        )

    entity = db.get(Entity, provider_entity_id)
    append_ledger_record(
        db,
        contribution_id=contribution_id,
        event_type="compute_provided",
        payload={
            "provider_entity_id": provider_entity_id,
            "provider_name": entity.name if entity else None,
            "consumer_entity_id": consumer_id,
            "capability": receipt.get("capability"),
            "adapter": receipt.get("adapter"),
            "model": receipt.get("model"),
            "credits_granted": provider_amount,
            "pocp_tokens_granted": provider_amount,
            "consumer_tokens": consumer_debited,
            "settlement": settlement_meta,
            "receipt_hash": receipt_hash,
            "job_id": receipt.get("job_id"),
            "usage": usage,
            "execution_mode": (receipt.get("extra") or {}).get("execution_mode"),
            "split_role": "compute" if split_shares else None,
        },
    )

    reputation = grant_compute_provider_reputation(
        db,
        receipt,
        consumer_entity_id=consumer_id,
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
            credits_granted=provider_amount,
            receipt_hash=receipt_hash,
        )
    except Exception:
        pool_deposit = None

    compute_settlement_payload: dict[str, Any] = {
        "provider_entity_id": provider_entity_id,
        "consumer_entity_id": consumer_id,
        "capability": receipt.get("capability"),
        "credits_granted": provider_amount,
        "pocp_tokens_granted": provider_amount,
        "consumer_tokens": consumer_debited,
        "settlement": settlement_meta,
        "reputation_granted": (reputation or {}).get("delta"),
        "reputation_category": (reputation or {}).get("category"),
        "receipt_hash": receipt_hash,
        "job_id": receipt.get("job_id"),
        "bilateral": not bool(split_shares),
        "multiparty_split": bool(split_shares),
        "usage": usage,
        "execution_mode": (receipt.get("extra") or {}).get("execution_mode"),
    }
    if split_shares:
        compute_settlement_payload.update(
            {
                "skill_entity_id": skill_entity_id,
                "skill_credits_granted": skill_credited,
                "protocol_fee_collected": protocol_credited,
                "protocol_treasury_entity_id": treasury_entity_id,
                "tokens_burned": burn_amount,
            }
        )
    append_ledger_record(
        db,
        contribution_id=contribution_id,
        event_type="compute_settlement",
        payload=compute_settlement_payload,
    )

    provider_ids = [provider_entity_id]
    if skill_entity_id and skill_credited > 0:
        provider_ids.append(skill_entity_id)
    if treasury_entity_id and protocol_credited > 0:
        provider_ids.append(treasury_entity_id)

    exchange_record = emit_exchange_settled(
        db,
        consumer_entity_id=consumer_id,
        provider_entity_ids=provider_ids,
        exchange_kind=infer_exchange_kind(receipt=receipt, skill_entity_id=skill_entity_id),
        credit_transactions=exchange_txs,
        receipt_hash=receipt_hash,
        capability=str(receipt.get("capability") or ""),
        usage=usage,
        contribution_id=contribution_id,
        legacy_event_type="compute_settlement",
        extra_payload={
            "settlement_kind": settlement_kind,
            "settlement": settlement_meta,
            "job_id": receipt.get("job_id"),
        },
    )
    db.flush()
    result: dict[str, Any] = {
        "settled": True,
        "exchange_id": (exchange_record.payload or {}).get("exchange_id"),
        "exchange_ledger_record_id": exchange_record.id,
        "bilateral": not bool(split_shares),
        "multiparty_split": bool(split_shares),
        "provider_entity_id": provider_entity_id,
        "consumer_entity_id": consumer_id,
        "credits_granted": provider_amount,
        "pocp_tokens_granted": provider_amount,
        "consumer_tokens": consumer_debited,
        "consumer_debited": consumer_debited > 0,
        "metering_mode": (usage or {}).get("metering_mode") if usage else None,
        "settlement": settlement_meta,
        "remaining_tokens": provider_wallet.ai_credits,
        "remaining_credits": provider_wallet.ai_credits,
        "consumer_remaining_tokens": consumer_wallet.ai_credits if consumer_wallet else None,
        "receipt_hash": receipt_hash,
        "reputation": reputation,
        "pool_deposit": pool_deposit,
    }
    if split_shares:
        result.update(
            {
                "skill_entity_id": skill_entity_id,
                "skill_credits_granted": skill_credited,
                "protocol_fee_collected": protocol_credited,
                "protocol_treasury_entity_id": treasury_entity_id,
                "tokens_burned": burn_amount,
                "split": split_shares,
            }
        )
    return result


def settle_intel_provider(
    db: Session,
    *,
    provider_entity_id: str,
    service: str,
    consumer_entity_id: str,
    contribution_id: str | None = None,
    task_id: str | None = None,
    intel_receipt: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Debit consumer and credit intelligence provider (witness, skill, matching)."""
    if intel_receipt:
        receipt_hash = (intel_receipt.get("integrity") or {}).get("receipt_hash")
        usage = intel_receipt.get("usage") or {}
        service = str(intel_receipt.get("service") or service)
    else:
        body = {
            "provider_entity_id": provider_entity_id,
            "service": service,
            "contribution_id": contribution_id,
            "task_id": task_id,
            "consumer_entity_id": consumer_entity_id,
        }
        receipt_hash = hashlib.sha256(
            json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        from services.compute_metering import intel_usage_for_service

        usage = intel_usage_for_service(service)
        usage["service"] = service

    if not receipt_hash:
        return None

    prov_reason = f"intel_provided:{receipt_hash[:16]}"
    provider_wallet = _wallet(db, provider_entity_id)
    if provider_wallet is None:
        return None
    if _tx_exists(db, provider_wallet.id, prov_reason):
        return {
            "settled": False,
            "reason": "already_settled",
            "provider_entity_id": provider_entity_id,
            "receipt_hash": receipt_hash,
        }

    listing_consumer, listing_provider = resolve_intel_listing_price(
        db, provider_entity_id=provider_entity_id, service=service
    )
    if listing_provider is not None:
        provider_amount = float(listing_provider)
        consumer_amount = float(listing_consumer or listing_provider)
    else:
        from services.compute_metering import intel_usage_for_service

        intel_cfg = (get_rewards_config().get("compute_metering") or {}).get("intel") or {}
        svc = intel_cfg.get(service) or {}
        provider_amount = float(svc.get("provider_tokens", svc.get("provider_credits", 3.0)))
        consumer_amount = float(svc.get("consumer_tokens", svc.get("consumer_credits", 5.0)))

    if provider_entity_id == consumer_entity_id:
        consumer_amount = 0.0

    consumer_wallet = _wallet(db, consumer_entity_id)
    consumer_debited = 0.0
    exchange_txs: list[CreditTransaction] = []
    if consumer_amount > 0:
        if consumer_wallet is None:
            return {
                "settled": False,
                "reason": "consumer_wallet_missing",
                "consumer_entity_id": consumer_entity_id,
            }
        from services.anti_abuse import check_daily_ai_burn_limit

        check_daily_ai_burn_limit(db, consumer_entity_id, consumer_amount)
        if consumer_wallet.ai_credits < consumer_amount:
            return {
                "settled": False,
                "reason": "insufficient_consumer_balance",
                "consumer_entity_id": consumer_entity_id,
                "required_tokens": consumer_amount,
                "available_tokens": consumer_wallet.ai_credits,
            }
        consumer_wallet.ai_credits -= consumer_amount
        consumer_debited = consumer_amount
        consumer_tx = CreditTransaction(
            wallet_id=consumer_wallet.id,
            amount=-consumer_amount,
            credit_type=CreditType.ai_credits,
            reason=f"intel_consumed:{receipt_hash[:16]}",
            contribution_id=contribution_id,
        )
        db.add(consumer_tx)
        exchange_txs.append(consumer_tx)

    provider_wallet.ai_credits += provider_amount
    provider_tx = CreditTransaction(
        wallet_id=provider_wallet.id,
        amount=provider_amount,
        credit_type=CreditType.ai_credits,
        reason=prov_reason,
        contribution_id=contribution_id,
    )
    db.add(provider_tx)
    exchange_txs.append(provider_tx)

    settlement_meta = settlement_block(
        usage,
        pocp_tokens_consumer=consumer_debited,
        pocp_tokens_provider=provider_amount,
    )
    append_ledger_record(
        db,
        contribution_id=contribution_id,
        event_type="intel_provided",
        payload={
            "provider_entity_id": provider_entity_id,
            "consumer_entity_id": consumer_entity_id,
            "service": service,
            "credits_granted": provider_amount,
            "pocp_tokens_granted": provider_amount,
            "consumer_tokens": consumer_debited,
            "settlement": settlement_meta,
            "receipt_hash": receipt_hash,
            "task_id": task_id,
        },
    )
    if consumer_debited > 0:
        append_ledger_record(
            db,
            contribution_id=contribution_id,
            event_type="ai_credits_burned",
            payload={
                "entity_id": consumer_entity_id,
                "credits_spent": consumer_debited,
                "pocp_tokens_spent": consumer_debited,
                "service": service,
                "receipt_hash": receipt_hash,
                "settlement_kind": "intel",
            },
        )
    exchange_record = emit_exchange_settled(
        db,
        consumer_entity_id=consumer_entity_id,
        provider_entity_ids=[provider_entity_id],
        exchange_kind=infer_exchange_kind(service=service),
        credit_transactions=exchange_txs,
        receipt_hash=receipt_hash,
        capability=service,
        usage=usage,
        contribution_id=contribution_id,
        legacy_event_type="intel_provided",
        extra_payload={"service": service, "task_id": task_id, "settlement": settlement_meta},
    )
    db.flush()
    return {
        "settled": True,
        "exchange_id": (exchange_record.payload or {}).get("exchange_id"),
        "exchange_ledger_record_id": exchange_record.id,
        "bilateral": True,
        "kind": "intel",
        "provider_entity_id": provider_entity_id,
        "consumer_entity_id": consumer_entity_id,
        "service": service,
        "credits_granted": provider_amount,
        "consumer_tokens": consumer_debited,
        "consumer_debited": consumer_debited > 0,
        "receipt_hash": receipt_hash,
        "settlement": settlement_meta,
        "remaining_tokens": provider_wallet.ai_credits,
        "consumer_remaining_tokens": consumer_wallet.ai_credits if consumer_wallet else None,
    }


def settle_compute_provider(
    db: Session,
    receipt: dict[str, Any],
    *,
    consumer_entity_id: str | None = None,
    selected_provider: dict[str, Any] | None = None,
    skill_entity_id: str | None = None,
) -> dict[str, Any] | None:
    """Grant provider + debit consumer (bilateral, skill split, or federation)."""
    from services.federation_settlement import settle_compute_receipt

    return settle_compute_receipt(
        db,
        receipt,
        consumer_entity_id=consumer_entity_id,
        selected_provider=selected_provider,
        skill_entity_id=skill_entity_id,
    )
