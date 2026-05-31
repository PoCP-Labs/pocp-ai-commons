"""User-facing wallet queries — balances, transaction history, spend quotes."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from models.wallet import CreditTransaction, CreditType, Wallet
from services.ai_chat import AI_CHAT_COST_PER_MESSAGE
from services.rights import get_or_create_wallet, rights_policy
from services.wallet_audit import audit_wallet_by_entity, compute_balances_from_transactions
from services.wallet_ledger_link import batch_ledger_links, transaction_category


def _day_start() -> datetime:
    now = datetime.utcnow()
    return datetime(now.year, now.month, now.day)


def _balance_after_map(transactions: list[CreditTransaction]) -> dict[str, dict[str, float]]:
    """Replay ascending txs → per-tx running balances keyed by transaction id."""
    cp = 0.0
    bc = 0.0
    result: dict[str, dict[str, float]] = {}
    for tx in transactions:
        if tx.credit_type == CreditType.cp:
            cp += float(tx.amount)
        elif tx.credit_type == CreditType.ai_credits:
            bc += float(tx.amount)
        result[tx.id] = {
            "cp_balance": round(cp, 6),
            "ai_credits": round(bc, 6),
        }
    return result


def wallet_summary(db: Session, entity_id: str) -> dict:
    wallet = db.query(Wallet).filter(Wallet.entity_id == entity_id).first()
    if wallet is None:
        wallet = get_or_create_wallet(db, entity_id)
        db.flush()

    day = _day_start()
    txs = (
        db.query(CreditTransaction)
        .filter(CreditTransaction.wallet_id == wallet.id)
        .order_by(CreditTransaction.created_at.asc(), CreditTransaction.id.asc())
        .all()
    )

    today_earned = {"cp": 0.0, "ai_credits": 0.0}
    today_spent = {"cp": 0.0, "ai_credits": 0.0}
    today_compute_earned = 0.0
    today_compute_spent = 0.0
    for tx in txs:
        if tx.created_at < day:
            continue
        key = "cp" if tx.credit_type == CreditType.cp else "ai_credits"
        amount = float(tx.amount)
        cat = transaction_category(tx.reason, amount)
        if cat == "compute_earn" and tx.credit_type == CreditType.ai_credits and amount > 0:
            today_compute_earned = round(today_compute_earned + amount, 6)
        if cat == "compute_spend" and amount < 0:
            today_compute_spent = round(today_compute_spent + abs(amount), 6)
        if amount >= 0:
            today_earned[key] = round(today_earned[key] + amount, 6)
        else:
            today_spent[key] = round(today_spent[key] + abs(amount), 6)

    policies = rights_policy()
    audit = audit_wallet_by_entity(db, entity_id)

    return {
        "entity_id": entity_id,
        "wallet_id": wallet.id,
        "cp_balance": round(float(wallet.cp_balance), 6),
        "ai_credits": round(float(wallet.ai_credits), 6),
        "today_earned": today_earned,
        "today_spent": today_spent,
        "today_compute_earned": today_compute_earned,
        "today_compute_spent": today_compute_spent,
        "transaction_count": len(txs),
        "audit_valid": audit["valid"] if audit else True,
        "rights_policy": {
            "cp": {
                "version": policies["cp"].version,
                "spendable": policies["cp"].spendable,
                "transferable": policies["cp"].transferable,
                "description": policies["cp"].description,
            },
            "bc": {
                "version": policies["bc"].version,
                "spendable": policies["bc"].spendable,
                "transferable": policies["bc"].transferable,
                "description": policies["bc"].description,
            },
        },
    }


def list_wallet_transactions(
    db: Session,
    entity_id: str,
    *,
    limit: int = 50,
    offset: int = 0,
    credit_type: CreditType | None = None,
) -> dict:
    wallet = db.query(Wallet).filter(Wallet.entity_id == entity_id).first()
    if wallet is None:
        return {"items": [], "total": 0, "limit": limit, "offset": offset}

    all_q = (
        db.query(CreditTransaction)
        .filter(CreditTransaction.wallet_id == wallet.id)
        .order_by(CreditTransaction.created_at.asc(), CreditTransaction.id.asc())
    )
    all_txs = all_q.all()
    after_map = _balance_after_map(all_txs)

    filtered = list(reversed(all_txs))
    if credit_type is not None:
        filtered = [t for t in filtered if t.credit_type == credit_type]

    total = len(filtered)
    page = filtered[offset : offset + limit]
    ledger_links = batch_ledger_links(db, wallet, page)

    items = []
    for tx in page:
        bal = after_map.get(tx.id, {})
        amount = round(float(tx.amount), 6)
        item = {
            "id": tx.id,
            "wallet_id": tx.wallet_id,
            "contribution_id": tx.contribution_id,
            "amount": amount,
            "credit_type": tx.credit_type.value,
            "reason": tx.reason,
            "category": transaction_category(tx.reason, amount),
            "created_at": tx.created_at.isoformat(),
            "balance_after": {
                "cp_balance": bal.get("cp_balance", 0.0),
                "ai_credits": bal.get("ai_credits", 0.0),
            },
        }
        link = ledger_links.get(tx.id)
        if link:
            item["ledger_link"] = link
        items.append(item)

    return {"items": items, "total": total, "limit": limit, "offset": offset}


def export_wallet_bundle(db: Session, entity_id: str) -> dict:
    """Personal wallet export for offline audit (single Entity)."""
    from datetime import datetime

    from services.protocol_config import get_rewards_config

    wallet = db.query(Wallet).filter(Wallet.entity_id == entity_id).first()
    if wallet is None:
        wallet = get_or_create_wallet(db, entity_id)
        db.flush()

    txs = (
        db.query(CreditTransaction)
        .filter(CreditTransaction.wallet_id == wallet.id)
        .order_by(CreditTransaction.created_at.asc(), CreditTransaction.id.asc())
        .all()
    )
    audit = audit_wallet_by_entity(db, entity_id)
    tx_payload = list_wallet_transactions(db, entity_id, limit=max(len(txs), 1), offset=0)
    wallet_dict = {
        "id": wallet.id,
        "entity_id": wallet.entity_id,
        "cp_balance": wallet.cp_balance,
        "ai_credits": wallet.ai_credits,
    }
    verify_transactions = [
        {
            "id": t.id,
            "wallet_id": t.wallet_id,
            "contribution_id": t.contribution_id,
            "amount": float(t.amount),
            "credit_type": t.credit_type.value,
            "reason": t.reason,
            "created_at": t.created_at.isoformat(),
        }
        for t in txs
    ]

    return {
        "spec_version": get_rewards_config().get("spec_version", "0.1"),
        "export_kind": "wallet_entity_v0.1",
        "exported_at": datetime.utcnow().isoformat(),
        "entity_id": entity_id,
        "wallet": wallet_dict,
        "wallets": [wallet_dict],
        "summary": wallet_summary(db, entity_id),
        "audit": audit,
        "transactions": verify_transactions,
        "transactions_enriched": tx_payload["items"],
    }


def verify_entity_wallet_export(export: dict) -> dict:
    """Verify a GET /wallets/me/export bundle (replay + optional embedded audit)."""
    from services.wallet_audit import verify_wallet_export

    replay = verify_wallet_export(export)
    embedded = export.get("audit")
    if embedded and embedded.get("valid") is False:
        replay["valid"] = False
        replay["embedded_audit_mismatch"] = True
    replay["export_kind"] = export.get("export_kind")
    replay["entity_id"] = export.get("entity_id")
    return replay


def quote_spend(db: Session, entity_id: str, action: str, **kwargs) -> dict:
    action = (action or "").lower()
    wallet = db.query(Wallet).filter(Wallet.entity_id == entity_id).first()
    balance = float(wallet.ai_credits) if wallet else 0.0

    if action == "ai_chat":
        cost = float(kwargs.get("cost") or AI_CHAT_COST_PER_MESSAGE)
        allowed = balance >= cost
        return {
            "action": action,
            "credit_type": CreditType.ai_credits.value,
            "cost": cost,
            "current_balance": round(balance, 6),
            "balance_after": round(balance - cost, 6) if allowed else round(balance, 6),
            "allowed": allowed,
            "provider": kwargs.get("provider"),
        }

    raise ValueError(f"Unsupported quote action: {action}")


def verify_wallet_balances(db: Session, wallet: Wallet) -> bool:
    txs = (
        db.query(CreditTransaction)
        .filter(CreditTransaction.wallet_id == wallet.id)
        .order_by(CreditTransaction.created_at.asc(), CreditTransaction.id.asc())
        .all()
    )
    computed = compute_balances_from_transactions(txs)
    return (
        round(float(wallet.cp_balance), 6) == computed["cp_balance"]
        and round(float(wallet.ai_credits), 6) == computed["ai_credits"]
    )
