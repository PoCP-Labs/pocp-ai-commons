"""Opt-in contribution upgrade from a settled exchange (Phase 4)."""

from __future__ import annotations

import os
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from genesis import LUMEN_0_ID
from models.contribution import ContributionEvent, ContributionStatus, ParticipantRole
from models.entity import Entity, EntityType
from services.contribution_submit import submit_contribution_event
from services.entity_local_chain import find_exchange_ledger_record
from services.evidence import POCP_META_KEY, enrich_evidence
from services.ledger_chain import append_ledger_record

WITNESS_WEIGHT = 0.03
CREATOR_WEIGHT = 0.4
CONTRIBUTION_PATH = "exchange_upgrade"

def _find_contribution_for_exchange(db: Session, exchange_id: str) -> ContributionEvent | None:
    for row in (
        db.query(ContributionEvent)
        .filter(ContributionEvent.status != ContributionStatus.rejected)
        .order_by(ContributionEvent.created_at.desc())
        .limit(500)
        .all()
    ):
        upgrade = (row.evidence or {}).get("exchange_upgrade") or {}
        if upgrade.get("exchange_id") == exchange_id:
            return row
    return None


def _provider_role(entity: Entity | None) -> ParticipantRole:
    if entity is None:
        return ParticipantRole.model_provider
    if entity.entity_type == EntityType.skill:
        return ParticipantRole.skill_provider
    if entity.entity_type == EntityType.agent:
        return ParticipantRole.executor
    if entity.entity_type == EntityType.llm:
        return ParticipantRole.model_provider
    if entity.entity_type == EntityType.human:
        return ParticipantRole.executor
    return ParticipantRole.model_provider


def _witness_entity_id() -> str:
    return os.getenv("POCP_EXCHANGE_WITNESS_ENTITY_ID", LUMEN_0_ID)


def _default_participants(
    db: Session,
    *,
    consumer_entity_id: str,
    provider_entity_ids: list[str],
    witness_entity_id: str | None = None,
) -> list[dict[str, Any]]:
    participants: list[dict[str, Any]] = [
        {"entity_id": consumer_entity_id, "role": ParticipantRole.creator.value, "weight": CREATOR_WEIGHT},
    ]
    providers = [pid for pid in provider_entity_ids if pid and pid != consumer_entity_id]
    provider_budget = 1.0 - CREATOR_WEIGHT - (WITNESS_WEIGHT if witness_entity_id else 0.0)
    if providers and provider_budget > 0:
        share = round(provider_budget / len(providers), 4)
        entities = {
            e.id: e for e in db.query(Entity).filter(Entity.id.in_(providers)).all()
        }
        for pid in providers:
            participants.append(
                {
                    "entity_id": pid,
                    "role": _provider_role(entities.get(pid)).value,
                    "weight": share,
                }
            )
    if witness_entity_id and witness_entity_id != consumer_entity_id:
        participants.append(
            {
                "entity_id": witness_entity_id,
                "role": ParticipantRole.witness.value,
                "weight": WITNESS_WEIGHT,
                "evidence": {"action": "exchange_upgrade witness (advisory)"},
            }
        )
    return participants

def publish_contribution_from_exchange(
    db: Session,
    *,
    exchange_id: str,
    human_entity_id: str,
    task_id: str,
    description: str | None = None,
    contribution_type: str = "knowledge",
    extra_evidence: dict[str, Any] | None = None,
) -> ContributionEvent:
    """Attach a settled exchange as evidence and submit a contribution (witness path)."""
    existing = _find_contribution_for_exchange(db, exchange_id)
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "Contribution already published for this exchange",
                "contribution_id": existing.id,
            },
        )

    record = find_exchange_ledger_record(db, exchange_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Exchange not found")

    payload = record.payload or {}
    consumer_id = payload.get("consumer_entity_id")
    if consumer_id != human_entity_id:
        raise HTTPException(
            status_code=403,
            detail="Only the exchange consumer may publish from this receipt",
        )

    provider_ids = list(payload.get("provider_entity_ids") or [])
    exchange_kind = payload.get("exchange_kind") or "capability"
    receipt_hash = payload.get("receipt_hash")
    trace_id = payload.get("invocation_trace_id")

    summary = description or (
        f"Work promoted from {exchange_kind} exchange {exchange_id}"
        + (f" (trace {trace_id[:12]}…)" if trace_id else "")
    )

    evidence: dict[str, Any] = {
        "content_preview": summary,
        "contribution_path": CONTRIBUTION_PATH,
        "witness_required": True,
        "exchange_upgrade": {
            "exchange_id": exchange_id,
            "exchange_kind": exchange_kind,
            "receipt_hash": receipt_hash,
            "invocation_trace_id": trace_id,
            "ledger_record_id": record.id,
            "ledger_record_hash": record.record_hash,
            "capability": payload.get("capability"),
            "capability_id": payload.get("capability_id"),
            "usage": payload.get("usage"),
            "consumer_entity_id": human_entity_id,
        },
    }
    if extra_evidence:        evidence.update(extra_evidence)
    evidence = enrich_evidence(evidence)

    provenance = {
        "creation_mode": "ai_assisted",
        "ai_tools_used": [f"exchange:{exchange_id}"],
        "notes": f"Upgraded from metered {exchange_kind} exchange; BC already settled on Exchange Chain.",
    }

    witness_id = _witness_entity_id()
    participants = _default_participants(
        db,
        consumer_entity_id=human_entity_id,
        provider_entity_ids=provider_ids,
        witness_entity_id=witness_id,
    )
    contribution = submit_contribution_event(
        db,
        human_entity_id=human_entity_id,
        task_id=task_id,
        contribution_type=contribution_type,
        description=summary,
        evidence=evidence,
        participants=participants,
        provenance=provenance,
    )

    meta = dict((contribution.evidence or {}).get(POCP_META_KEY) or {})
    meta["exchange_upgrade"] = evidence["exchange_upgrade"]
    meta["contribution_path"] = CONTRIBUTION_PATH
    merged = dict(contribution.evidence or {})
    merged[POCP_META_KEY] = meta
    contribution.evidence = merged
    db.add(contribution)
    db.flush()

    append_ledger_record(
        db,
        contribution_id=contribution.id,
        event_type="exchange_promoted_to_contribution",
        payload={
            "exchange_id": exchange_id,
            "contribution_id": contribution.id,
            "consumer_entity_id": human_entity_id,
            "witness_entity_id": witness_id,
            "contribution_path": CONTRIBUTION_PATH,
            "exchange_kind": exchange_kind,
        },
    )
    db.flush()
    return contribution