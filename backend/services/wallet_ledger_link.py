"""Link credit_transactions to ledger_records for wallet UI audit trails."""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy.orm import Session

from models.ledger import LedgerRecord
from models.wallet import CreditTransaction, CreditType, Wallet


def transaction_category(reason: str | None, amount: float) -> str:
    r = (reason or "").lower()
    if r.startswith("compute_consumed") or r.startswith("intel_consumed"):
        return "compute_spend"
    if r.startswith("compute_") or r.startswith("skill_orchestration") or r.startswith("protocol_fee"):
        return "compute_earn"
    if "contribution reward" in r or "contribution proof" in r or "entity-equal" in r:
        return "contribution"
    if "registration" in r:
        return "registration"
    if "ai chat" in r:
        return "ai_chat"
    if r.startswith("federation"):
        return "federation"
    return "credit" if amount >= 0 else "debit"


def _ledger_ref(record: LedgerRecord) -> dict:
    return {
        "ledger_record_id": record.id,
        "ledger_event_type": record.event_type,
        "ledger_record_hash": record.record_hash,
        "ledger_created_at": record.created_at.isoformat() if record.created_at else None,
    }


def _payload_entity_id(payload: dict | None) -> str | None:
    if not payload:
        return None
    for key in ("entity_id", "provider_entity_id", "consumer_entity_id", "treasury_entity_id"):
        val = payload.get(key)
        if val:
            return str(val)
    return None


def _matches_transaction(
    tx: CreditTransaction,
    wallet: Wallet,
    record: LedgerRecord,
) -> bool:
    payload = record.payload or {}
    reason = (tx.reason or "").lower()
    amount = abs(float(tx.amount))
    entity_id = wallet.entity_id

    if tx.contribution_id and record.contribution_id == tx.contribution_id:
        if record.event_type == "contribution_approved" and tx.amount > 0:
            return True
        if record.event_type == "compute_provided" and tx.amount > 0:
            return payload.get("provider_entity_id") == entity_id and float(
                payload.get("credits_granted") or payload.get("pocp_tokens_granted") or 0
            ) == amount
        if record.event_type == "intel_provided" and tx.amount > 0:
            return payload.get("provider_entity_id") == entity_id and float(
                payload.get("credits_granted") or payload.get("pocp_tokens_granted") or 0
            ) == amount
        if record.event_type == "protocol_fee_collected" and tx.amount > 0:
            return payload.get("treasury_entity_id") == entity_id
        if record.event_type == "ai_credits_burned" and tx.amount < 0:
            return payload.get("wallet_id") == wallet.id or payload.get("entity_id") == entity_id

    if record.event_type == "registration_grant" and tx.amount > 0:
        grants = payload.get("rights") or []
        if payload.get("entity_id") == entity_id:
            return True
        if any(g.get("entity_id") == entity_id for g in grants if isinstance(g, dict)):
            return True
        if payload.get("ai_credits") == amount and payload.get("entity_id") == entity_id:
            return True

    if record.event_type == "exchange_settled" and tx.ledger_record_id == record.id:
        tx_ids = payload.get("credit_transaction_ids") or []
        return tx.id in tx_ids or tx.ledger_record_id == record.id

    if record.event_type == "ai_credits_burned" and tx.amount < 0:
        if payload.get("wallet_id") == wallet.id:
            spent = float(payload.get("credits_spent") or payload.get("pocp_tokens_spent") or 0)
            if spent == amount and "receipt_hash" not in payload:
                return reason == "ai chat usage"
            if spent == amount:
                return True

    if record.event_type == "compute_provided" and tx.amount > 0:
        return payload.get("provider_entity_id") == entity_id and float(
            payload.get("credits_granted") or payload.get("pocp_tokens_granted") or 0
        ) == amount

    if record.event_type == "intel_provided" and tx.amount > 0:
        return payload.get("provider_entity_id") == entity_id and float(
            payload.get("credits_granted") or payload.get("pocp_tokens_granted") or 0
        ) == amount

    return False


def resolve_ledger_link(
    db: Session,
    tx: CreditTransaction,
    wallet: Wallet,
    *,
    nearby_records: list[LedgerRecord] | None = None,
    contribution_records: dict[str, list[LedgerRecord]] | None = None,
) -> dict | None:
    if tx.ledger_record_id:
        record = db.get(LedgerRecord, tx.ledger_record_id)
        if record:
            return _ledger_ref(record)

    candidates: list[LedgerRecord] = []
    if tx.contribution_id and contribution_records:
        candidates.extend(contribution_records.get(tx.contribution_id, []))

    if nearby_records:
        window_start = tx.created_at - timedelta(seconds=120)
        window_end = tx.created_at + timedelta(seconds=120)
        for record in nearby_records:
            if window_start <= record.created_at <= window_end:
                candidates.append(record)

    if not candidates:
        if tx.contribution_id:
            candidates = (
                db.query(LedgerRecord)
                .filter(LedgerRecord.contribution_id == tx.contribution_id)
                .order_by(LedgerRecord.created_at.asc())
                .all()
            )
        else:
            window_start = tx.created_at - timedelta(seconds=120)
            window_end = tx.created_at + timedelta(seconds=120)
            candidates = (
                db.query(LedgerRecord)
                .filter(
                    LedgerRecord.created_at >= window_start,
                    LedgerRecord.created_at <= window_end,
                )
                .order_by(LedgerRecord.created_at.asc())
                .all()
            )

    seen: set[str] = set()
    for record in candidates:
        if record.id in seen:
            continue
        seen.add(record.id)
        if _matches_transaction(tx, wallet, record):
            return _ledger_ref(record)
    return None


def batch_ledger_links(
    db: Session,
    wallet: Wallet,
    transactions: list[CreditTransaction],
) -> dict[str, dict]:
    if not transactions:
        return {}

    contribution_ids = {tx.contribution_id for tx in transactions if tx.contribution_id}
    contribution_records: dict[str, list[LedgerRecord]] = {}
    if contribution_ids:
        rows = (
            db.query(LedgerRecord)
            .filter(LedgerRecord.contribution_id.in_(contribution_ids))
            .order_by(LedgerRecord.created_at.asc())
            .all()
        )
        for row in rows:
            if row.contribution_id:
                contribution_records.setdefault(row.contribution_id, []).append(row)

    min_at = min(tx.created_at for tx in transactions)
    max_at = max(tx.created_at for tx in transactions)
    nearby = (
        db.query(LedgerRecord)
        .filter(
            LedgerRecord.created_at >= min_at - timedelta(seconds=120),
            LedgerRecord.created_at <= max_at + timedelta(seconds=120),
        )
        .order_by(LedgerRecord.created_at.asc())
        .all()
    )

    links: dict[str, dict] = {}
    for tx in transactions:
        link = resolve_ledger_link(
            db,
            tx,
            wallet,
            nearby_records=nearby,
            contribution_records=contribution_records,
        )
        if link:
            links[tx.id] = link
    return links
