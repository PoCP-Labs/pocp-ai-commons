"""Federation cross-node PoCP Token settlement — v0.4 bilateral accounting."""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from models.entity import Entity
from models.federation import FederationSettlement
from models.wallet import CreditTransaction, CreditType, Wallet
from services.compute_metering import settlement_block
from services.compute_receipt import verify_compute_receipt
from services.compute_settlement import compute_consumer_tokens, compute_provider_tokens
from services.federation_community import local_federation_entity_id
from services.federation_crypto import sign_message, verify_message
from services.ledger_chain import append_ledger_record
from services.trust_config import trusted_nodes_map

SPEC_VERSION = "pocp.federation_settlement.v0.4"


def _local_node_id() -> str:
    return os.getenv("POCP_NODE_ID", f"pocp-node-{uuid.uuid4().hex[:8]}")


def is_federation_peer_execution(
    receipt: dict[str, Any],
    selected_provider: dict[str, Any] | None = None,
) -> bool:
    extra = receipt.get("extra") or {}
    source = extra.get("source") or (selected_provider or {}).get("source")
    return source == "peer_node"


def settlement_intent_message(
    *,
    consumer_node_id: str,
    provider_node_id: str,
    receipt_hash: str,
    consumer_entity_id: str,
    consumer_tokens: float,
    provider_tokens: float,
) -> str:
    return "|".join(
        [
            consumer_node_id,
            provider_node_id,
            receipt_hash,
            consumer_entity_id,
            f"{consumer_tokens:.6f}",
            f"{provider_tokens:.6f}",
        ]
    )


def _wallet(db: Session, entity_id: str) -> Wallet | None:
    return db.query(Wallet).filter(Wallet.entity_id == entity_id).first()


def _settlement_exists(db: Session, settlement_key: str, side: str) -> FederationSettlement | None:
    return (
        db.query(FederationSettlement)
        .filter(
            FederationSettlement.settlement_key == settlement_key,
            FederationSettlement.side == side,
        )
        .first()
    )


def _resolve_provider_credit_entity(
    db: Session,
    provider_entity_id: str | None,
) -> tuple[str, Wallet | None]:
    if provider_entity_id:
        wallet = _wallet(db, provider_entity_id)
        if wallet is not None:
            return provider_entity_id, wallet
    local_id = local_federation_entity_id()
    return local_id, _wallet(db, local_id)


def build_settlement_intent(
    *,
    receipt: dict[str, Any],
    consumer_node_id: str,
    provider_node_id: str,
    consumer_entity_id: str,
    consumer_tokens: float,
    provider_tokens: float,
) -> dict[str, Any]:
    receipt_hash = (receipt.get("integrity") or {}).get("receipt_hash") or ""
    message = settlement_intent_message(
        consumer_node_id=consumer_node_id,
        provider_node_id=provider_node_id,
        receipt_hash=receipt_hash,
        consumer_entity_id=consumer_entity_id,
        consumer_tokens=consumer_tokens,
        provider_tokens=provider_tokens,
    )
    return {
        "spec_version": SPEC_VERSION,
        "consumer_node_id": consumer_node_id,
        "provider_node_id": provider_node_id,
        "consumer_entity_id": consumer_entity_id,
        "provider_entity_id": receipt.get("provider_entity_id"),
        "receipt_hash": receipt_hash,
        "receipt": receipt,
        "consumer_tokens": consumer_tokens,
        "provider_tokens": provider_tokens,
        "capability": receipt.get("capability"),
        "contribution_id": receipt.get("contribution_id"),
        "job_id": receipt.get("job_id"),
        "message": message,
        "signature": sign_message(message),
    }


def _verify_intent_signature(intent: dict[str, Any]) -> None:
    consumer_node_id = str(intent.get("consumer_node_id") or "")
    trusted = trusted_nodes_map().get(consumer_node_id)
    signature = intent.get("signature")
    message = intent.get("message")
    if not signature or not message:
        raise ValueError("Settlement intent missing signature or message")
    if trusted and trusted.public_key:
        if not verify_message(message, signature, trusted.public_key):
            raise ValueError(f"Invalid settlement intent signature from {consumer_node_id}")
        return
    if os.getenv("POCP_FEDERATION_SETTLEMENT_REQUIRE_SIGNATURE", "false").lower() in (
        "true",
        "1",
        "yes",
        "on",
    ):
        raise ValueError("Settlement intent signature required but not verified")


def push_settlement_intent(peer_base_url: str, intent: dict[str, Any], timeout: float = 12.0) -> dict[str, Any]:
    import urllib.error
    import urllib.request

    url = f"{peer_base_url.rstrip('/')}/api/v1/federation/settlement/intent"
    body = json.dumps(intent).encode()
    request = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode()
        return {"pushed": False, "error": f"HTTP {exc.code}", "detail": detail[:500]}
    except Exception as exc:
        return {"pushed": False, "error": str(exc)}


def settle_federation_cross_node(
    db: Session,
    receipt: dict[str, Any],
    *,
    consumer_entity_id: str | None = None,
    selected_provider: dict[str, Any] | None = None,
    push_intent: bool = True,
) -> dict[str, Any] | None:
    """Consumer-node settlement: debit local wallet and record cross-node intent."""
    if not verify_compute_receipt(receipt):
        return {"settled": False, "reason": "invalid_receipt"}

    receipt_hash = (receipt.get("integrity") or {}).get("receipt_hash")
    if not receipt_hash:
        return None

    provider_node_id = receipt.get("provider_node_id") or (selected_provider or {}).get("provider_node_id")
    peer_base_url = (receipt.get("extra") or {}).get("base_url") or (selected_provider or {}).get("base_url")
    if not provider_node_id:
        return {"settled": False, "reason": "missing_provider_node_id", "receipt_hash": receipt_hash}

    consumer_id = consumer_entity_id or receipt.get("initiator_entity_id")
    if not consumer_id:
        return None

    existing = _settlement_exists(db, receipt_hash, "consumer")
    if existing:
        return {
            "settled": False,
            "reason": "already_settled",
            "federation": True,
            "settlement_id": existing.id,
            "receipt_hash": receipt_hash,
        }

    consumer_amount = compute_consumer_tokens(receipt, db=db)
    provider_amount = compute_provider_tokens(receipt, db=db)
    contribution_id = receipt.get("contribution_id")
    usage = (receipt.get("extra") or {}).get("usage")
    consumer_debited = 0.0

    consumer_wallet = _wallet(db, consumer_id)
    if consumer_amount > 0:
        if consumer_wallet is None:
            return {
                "settled": False,
                "reason": "consumer_wallet_missing",
                "consumer_entity_id": consumer_id,
                "receipt_hash": receipt_hash,
                "federation": True,
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
                "federation": True,
            }
        consumer_wallet.ai_credits -= consumer_amount
        consumer_debited = consumer_amount
        db.add(
            CreditTransaction(
                wallet_id=consumer_wallet.id,
                amount=-consumer_amount,
                credit_type=CreditType.ai_credits,
                reason=f"federation_consumed:{receipt_hash[:16]}",
                contribution_id=contribution_id,
            )
        )
        append_ledger_record(
            db,
            contribution_id=contribution_id,
            event_type="ai_credits_burned",
            payload={
                "entity_id": consumer_id,
                "wallet_id": consumer_wallet.id,
                "credits_spent": consumer_amount,
                "pocp_tokens_spent": consumer_amount,
                "remaining_credits": consumer_wallet.ai_credits,
                "remaining_tokens": consumer_wallet.ai_credits,
                "receipt_hash": receipt_hash,
                "capability": receipt.get("capability"),
                "settlement_kind": "federation_cross_node",
                "provider_node_id": provider_node_id,
            },
        )

    settlement_meta = settlement_block(
        usage,
        pocp_tokens_consumer=consumer_debited,
        pocp_tokens_provider=provider_amount,
    )
    intent = build_settlement_intent(
        receipt=receipt,
        consumer_node_id=_local_node_id(),
        provider_node_id=str(provider_node_id),
        consumer_entity_id=consumer_id,
        consumer_tokens=consumer_debited,
        provider_tokens=provider_amount,
    )

    record = FederationSettlement(
        settlement_key=receipt_hash,
        side="consumer",
        status="consumer_debited",
        consumer_node_id=_local_node_id(),
        provider_node_id=str(provider_node_id),
        consumer_entity_id=consumer_id,
        provider_entity_id=receipt.get("provider_entity_id"),
        receipt_hash=receipt_hash,
        job_id=receipt.get("job_id"),
        contribution_id=contribution_id,
        capability=str(receipt.get("capability") or ""),
        consumer_tokens=consumer_debited,
        provider_tokens=provider_amount,
        intent_payload=intent,
        peer_base_url=str(peer_base_url).rstrip("/") if peer_base_url else None,
    )
    db.add(record)

    append_ledger_record(
        db,
        contribution_id=contribution_id,
        event_type="federation_settlement_intent",
        payload={
            "settlement_id": record.id,
            "consumer_node_id": _local_node_id(),
            "provider_node_id": provider_node_id,
            "consumer_entity_id": consumer_id,
            "provider_entity_id": receipt.get("provider_entity_id"),
            "consumer_tokens": consumer_debited,
            "provider_tokens": provider_amount,
            "receipt_hash": receipt_hash,
            "job_id": receipt.get("job_id"),
            "capability": receipt.get("capability"),
            "settlement": settlement_meta,
            "status": "consumer_debited",
        },
    )
    db.flush()

    mirror_result = None
    if push_intent and peer_base_url:
        mirror_result = push_settlement_intent(str(peer_base_url), intent)
        if mirror_result.get("settled") or mirror_result.get("status") == "provider_credited":
            record.status = "mirrored"
            record.mirrored_at = datetime.utcnow()
            db.flush()

    return {
        "settled": True,
        "federation": True,
        "bilateral": True,
        "cross_node": True,
        "settlement_id": record.id,
        "consumer_node_id": _local_node_id(),
        "provider_node_id": provider_node_id,
        "consumer_entity_id": consumer_id,
        "provider_entity_id": receipt.get("provider_entity_id"),
        "consumer_tokens": consumer_debited,
        "consumer_debited": consumer_debited > 0,
        "pocp_tokens_granted": provider_amount,
        "credits_granted": provider_amount,
        "settlement": settlement_meta,
        "receipt_hash": receipt_hash,
        "status": record.status,
        "mirror_push": mirror_result,
        "consumer_remaining_tokens": consumer_wallet.ai_credits if consumer_wallet else None,
    }


def apply_settlement_intent(db: Session, intent: dict[str, Any]) -> dict[str, Any]:
    """Provider-node mirror: credit local provider wallet from signed consumer intent."""
    receipt = intent.get("receipt") or {}
    if not verify_compute_receipt(receipt):
        raise ValueError("Invalid compute receipt in settlement intent")

    receipt_hash = str(intent.get("receipt_hash") or (receipt.get("integrity") or {}).get("receipt_hash") or "")
    if not receipt_hash:
        raise ValueError("Missing receipt_hash")

    provider_node_id = str(intent.get("provider_node_id") or receipt.get("provider_node_id") or _local_node_id())
    if provider_node_id != _local_node_id():
        raise ValueError(
            f"Settlement intent targets provider_node_id={provider_node_id}, local={_local_node_id()}"
        )

    _verify_intent_signature(intent)

    existing = _settlement_exists(db, receipt_hash, "provider")
    if existing:
        return {
            "settled": False,
            "reason": "already_settled",
            "settlement_id": existing.id,
            "status": existing.status,
            "receipt_hash": receipt_hash,
        }

    provider_amount = float(intent.get("provider_tokens") or compute_provider_tokens(receipt, db=db))
    consumer_amount = float(intent.get("consumer_tokens") or 0.0)
    consumer_entity_id = str(intent.get("consumer_entity_id") or receipt.get("initiator_entity_id") or "")
    provider_entity_id = intent.get("provider_entity_id") or receipt.get("provider_entity_id")
    contribution_id = intent.get("contribution_id") or receipt.get("contribution_id")
    usage = (receipt.get("extra") or {}).get("usage")

    credit_entity_id, provider_wallet = _resolve_provider_credit_entity(db, provider_entity_id)
    if provider_wallet is None:
        return {
            "settled": False,
            "reason": "provider_wallet_missing",
            "provider_entity_id": credit_entity_id,
            "receipt_hash": receipt_hash,
        }

    prov_reason = f"federation_provided:{receipt_hash[:16]}"
    provider_wallet.ai_credits += provider_amount
    db.add(
        CreditTransaction(
            wallet_id=provider_wallet.id,
            amount=provider_amount,
            credit_type=CreditType.ai_credits,
            reason=prov_reason,
            contribution_id=contribution_id,
        )
    )

    settlement_meta = settlement_block(
        usage,
        pocp_tokens_consumer=consumer_amount,
        pocp_tokens_provider=provider_amount,
    )
    entity = db.get(Entity, credit_entity_id)
    append_ledger_record(
        db,
        contribution_id=contribution_id,
        event_type="compute_provided",
        payload={
            "provider_entity_id": credit_entity_id,
            "provider_name": entity.name if entity else None,
            "consumer_entity_id": consumer_entity_id,
            "consumer_node_id": intent.get("consumer_node_id"),
            "capability": receipt.get("capability"),
            "adapter": receipt.get("adapter"),
            "model": receipt.get("model"),
            "credits_granted": provider_amount,
            "pocp_tokens_granted": provider_amount,
            "consumer_tokens": consumer_amount,
            "settlement": settlement_meta,
            "receipt_hash": receipt_hash,
            "job_id": receipt.get("job_id"),
            "federation_mirror": True,
        },
    )

    record = FederationSettlement(
        settlement_key=receipt_hash,
        side="provider",
        status="provider_credited",
        consumer_node_id=str(intent.get("consumer_node_id") or ""),
        provider_node_id=provider_node_id,
        consumer_entity_id=consumer_entity_id,
        provider_entity_id=credit_entity_id,
        receipt_hash=receipt_hash,
        job_id=receipt.get("job_id"),
        contribution_id=contribution_id,
        capability=str(receipt.get("capability") or intent.get("capability") or ""),
        consumer_tokens=consumer_amount,
        provider_tokens=provider_amount,
        intent_payload=intent,
        mirrored_at=datetime.utcnow(),
    )
    db.add(record)

    append_ledger_record(
        db,
        contribution_id=contribution_id,
        event_type="federation_settlement_mirrored",
        payload={
            "settlement_id": record.id,
            "consumer_node_id": intent.get("consumer_node_id"),
            "provider_node_id": provider_node_id,
            "consumer_entity_id": consumer_entity_id,
            "provider_entity_id": credit_entity_id,
            "consumer_tokens": consumer_amount,
            "provider_tokens": provider_amount,
            "receipt_hash": receipt_hash,
            "settlement": settlement_meta,
            "status": "provider_credited",
        },
    )
    db.flush()

    return {
        "settled": True,
        "federation": True,
        "cross_node": True,
        "settlement_id": record.id,
        "status": "provider_credited",
        "provider_entity_id": credit_entity_id,
        "consumer_entity_id": consumer_entity_id,
        "consumer_node_id": intent.get("consumer_node_id"),
        "provider_node_id": provider_node_id,
        "credits_granted": provider_amount,
        "pocp_tokens_granted": provider_amount,
        "consumer_tokens": consumer_amount,
        "receipt_hash": receipt_hash,
        "remaining_tokens": provider_wallet.ai_credits,
        "settlement": settlement_meta,
    }


def list_federation_settlements(
    db: Session,
    *,
    side: str | None = None,
    status: str | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    query = db.query(FederationSettlement).order_by(FederationSettlement.created_at.desc())
    if side:
        query = query.filter(FederationSettlement.side == side)
    if status:
        query = query.filter(FederationSettlement.status == status)
    rows = query.limit(max(1, min(limit, 200))).all()
    return {
        "spec_version": SPEC_VERSION,
        "local_node_id": _local_node_id(),
        "count": len(rows),
        "settlements": [
            {
                "id": row.id,
                "settlement_key": row.settlement_key,
                "side": row.side,
                "status": row.status,
                "consumer_node_id": row.consumer_node_id,
                "provider_node_id": row.provider_node_id,
                "consumer_entity_id": row.consumer_entity_id,
                "provider_entity_id": row.provider_entity_id,
                "receipt_hash": row.receipt_hash,
                "consumer_tokens": row.consumer_tokens,
                "provider_tokens": row.provider_tokens,
                "capability": row.capability,
                "job_id": row.job_id,
                "contribution_id": row.contribution_id,
                "peer_base_url": row.peer_base_url,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "mirrored_at": row.mirrored_at.isoformat() if row.mirrored_at else None,
            }
            for row in rows
        ],
    }


def settle_compute_receipt(
    db: Session,
    receipt: dict[str, Any],
    *,
    consumer_entity_id: str | None = None,
    selected_provider: dict[str, Any] | None = None,
    skill_entity_id: str | None = None,
) -> dict[str, Any] | None:
    """Route local bilateral vs federation cross-node settlement."""
    if is_federation_peer_execution(receipt, selected_provider):
        return settle_federation_cross_node(
            db,
            receipt,
            consumer_entity_id=consumer_entity_id,
            selected_provider=selected_provider,
        )
    from services.compute_settlement import settle_bilateral

    return settle_bilateral(
        db,
        receipt,
        consumer_entity_id=consumer_entity_id,
        skill_entity_id=skill_entity_id,
    )
