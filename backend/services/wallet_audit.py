"""Wallet balance audit — recompute CP / AI Credits from transactions only.

Bitcoin-inspired UTXO discipline: balances are derived state; transactions are truth.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from models.wallet import CreditTransaction, CreditType, Wallet


def compute_balances_from_transactions(
    transactions: list[CreditTransaction],
) -> dict[str, float]:
    cp = 0.0
    ai_credits = 0.0
    for tx in transactions:
        if tx.credit_type == CreditType.cp:
            cp += float(tx.amount)
        elif tx.credit_type == CreditType.ai_credits:
            ai_credits += float(tx.amount)
    return {
        "cp_balance": round(cp, 6),
        "ai_credits": round(ai_credits, 6),
    }


def audit_wallet_record(
    wallet: Wallet,
    transactions: list[CreditTransaction],
) -> dict:
    computed = compute_balances_from_transactions(transactions)
    stored_cp = round(float(wallet.cp_balance), 6)
    stored_bc = round(float(wallet.ai_credits), 6)
    cp_match = stored_cp == computed["cp_balance"]
    bc_match = stored_bc == computed["ai_credits"]
    return {
        "wallet_id": wallet.id,
        "entity_id": wallet.entity_id,
        "valid": cp_match and bc_match,
        "stored": {"cp_balance": stored_cp, "ai_credits": stored_bc},
        "computed_from_transactions": computed,
        "transaction_count": len(transactions),
        "mismatch": None
        if cp_match and bc_match
        else {
            "cp_delta": stored_cp - computed["cp_balance"],
            "ai_credits_delta": stored_bc - computed["ai_credits"],
        },
    }


def audit_all_wallets(db: Session) -> dict:
    wallets = db.query(Wallet).order_by(Wallet.entity_id.asc()).all()
    results = []
    invalid = 0
    for wallet in wallets:
        txs = (
            db.query(CreditTransaction)
            .filter(CreditTransaction.wallet_id == wallet.id)
            .order_by(CreditTransaction.created_at.asc(), CreditTransaction.id.asc())
            .all()
        )
        row = audit_wallet_record(wallet, txs)
        if not row["valid"]:
            invalid += 1
        results.append(row)
    return {
        "valid": invalid == 0,
        "wallet_count": len(wallets),
        "invalid_count": invalid,
        "wallets": results,
        "audit_model": "transaction_replay_v0.1",
        "note": "Balances must equal sum(credit_transactions); operator cannot silently mint.",
    }


def audit_wallet_by_entity(db: Session, entity_id: str) -> dict | None:
    wallet = db.query(Wallet).filter(Wallet.entity_id == entity_id).first()
    if wallet is None:
        return None
    txs = (
        db.query(CreditTransaction)
        .filter(CreditTransaction.wallet_id == wallet.id)
        .order_by(CreditTransaction.created_at.asc(), CreditTransaction.id.asc())
        .all()
    )
    return audit_wallet_record(wallet, txs)


def verify_wallet_export(export: dict) -> dict:
    """Verify wallet balances from an exported bundle (no DB)."""
    wallets = export.get("wallets") or []
    invalid = 0
    results = []
    for wallet in wallets:
        txs = [
            t
            for t in (export.get("transactions") or [])
            if t.get("wallet_id") == wallet.get("id")
        ]
        cp = sum(t["amount"] for t in txs if t.get("credit_type") == "cp")
        bc = sum(t["amount"] for t in txs if t.get("credit_type") == "ai_credits")
        stored_cp = round(float(wallet.get("cp_balance", 0)), 6)
        stored_bc = round(float(wallet.get("ai_credits", 0)), 6)
        computed_cp = round(cp, 6)
        computed_bc = round(bc, 6)
        valid = stored_cp == computed_cp and stored_bc == computed_bc
        if not valid:
            invalid += 1
        results.append(
            {
                "wallet_id": wallet.get("id"),
                "entity_id": wallet.get("entity_id"),
                "valid": valid,
                "stored": {"cp_balance": stored_cp, "ai_credits": stored_bc},
                "computed_from_transactions": {
                    "cp_balance": computed_cp,
                    "ai_credits": computed_bc,
                },
                "transaction_count": len(txs),
            }
        )
    return {
        "valid": invalid == 0,
        "wallet_count": len(wallets),
        "invalid_count": invalid,
        "wallets": results,
    }
