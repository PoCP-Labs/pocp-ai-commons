"""Challenge and appeal flow — AI advisory + human/accountable final."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from models.contribution import ContributionEvent, ContributionStatus
from models.contribution_dispute import ContributionDispute, DisputeKind, DisputeStatus
from services.evidence import hash_evidence
from services.ledger_chain import append_ledger_record


def _evidence_hash(evidence: dict | None) -> str | None:
    if not evidence:
        return None
    return hash_evidence(evidence)


def _serialize_dispute(row: ContributionDispute) -> dict[str, Any]:
    return {
        "id": row.id,
        "contribution_id": row.contribution_id,
        "parent_dispute_id": row.parent_dispute_id,
        "kind": row.kind.value,
        "status": row.status.value,
        "challenger_entity_id": row.challenger_entity_id,
        "reason": row.reason,
        "evidence_hash": row.evidence_hash,
        "resolution_entity_id": row.resolution_entity_id,
        "resolution_note": row.resolution_note,
        "metadata": row.metadata_ or {},
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "resolved_at": row.resolved_at.isoformat() if row.resolved_at else None,
    }


def list_disputes(db: Session, contribution_id: str) -> list[dict[str, Any]]:
    rows = (
        db.query(ContributionDispute)
        .filter(ContributionDispute.contribution_id == contribution_id)
        .order_by(ContributionDispute.created_at.asc())
        .all()
    )
    return [_serialize_dispute(row) for row in rows]


def challenge_contribution(
    db: Session,
    contribution: ContributionEvent,
    *,
    challenger_entity_id: str,
    reason: str,
    evidence: dict | None = None,
) -> ContributionDispute:
    if contribution.status not in (
        ContributionStatus.approved,
        ContributionStatus.rejected,
        ContributionStatus.ai_verified,
    ):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot challenge contribution in status: {contribution.status.value}",
        )
    if challenger_entity_id == contribution.primary_entity_id:
        raise HTTPException(status_code=403, detail="Primary contributor cannot challenge own submission")

    open_challenge = (
        db.query(ContributionDispute)
        .filter(
            ContributionDispute.contribution_id == contribution.id,
            ContributionDispute.kind == DisputeKind.challenge,
            ContributionDispute.status == DisputeStatus.open,
        )
        .first()
    )
    if open_challenge:
        raise HTTPException(status_code=409, detail="Open challenge already exists for this contribution")

    evidence_hash = _evidence_hash(evidence)
    dispute = ContributionDispute(
        contribution_id=contribution.id,
        kind=DisputeKind.challenge,
        status=DisputeStatus.open,
        challenger_entity_id=challenger_entity_id,
        reason=reason.strip(),
        evidence_hash=evidence_hash,
        metadata_={"evidence": evidence or {}},
    )
    db.add(dispute)
    contribution.status = ContributionStatus.challenged
    append_ledger_record(
        db,
        contribution_id=contribution.id,
        event_type="contribution_challenged",
        payload={
            "dispute_id": dispute.id,
            "challenger_entity_id": challenger_entity_id,
            "reason": reason,
            "evidence_hash": evidence_hash,
        },
    )
    db.flush()
    return dispute


def appeal_dispute(
    db: Session,
    contribution: ContributionEvent,
    *,
    appellant_entity_id: str,
    reason: str,
    parent_dispute_id: str | None = None,
) -> ContributionDispute:
    if contribution.status != ContributionStatus.challenged:
        raise HTTPException(
            status_code=400,
            detail="Appeal requires contribution status challenged",
        )
    if appellant_entity_id != contribution.primary_entity_id:
        raise HTTPException(status_code=403, detail="Only primary contributor may appeal a challenge")

    parent = None
    if parent_dispute_id:
        parent = db.query(ContributionDispute).filter(ContributionDispute.id == parent_dispute_id).first()
    if parent is None:
        parent = (
            db.query(ContributionDispute)
            .filter(
                ContributionDispute.contribution_id == contribution.id,
                ContributionDispute.kind == DisputeKind.challenge,
                ContributionDispute.status == DisputeStatus.open,
            )
            .order_by(ContributionDispute.created_at.desc())
            .first()
        )
    if parent is None:
        raise HTTPException(status_code=404, detail="No open challenge to appeal")

    dispute = ContributionDispute(
        contribution_id=contribution.id,
        parent_dispute_id=parent.id,
        kind=DisputeKind.appeal,
        status=DisputeStatus.open,
        challenger_entity_id=appellant_entity_id,
        reason=reason.strip(),
        metadata_={"parent_kind": parent.kind.value},
    )
    db.add(dispute)
    contribution.status = ContributionStatus.appealed
    append_ledger_record(
        db,
        contribution_id=contribution.id,
        event_type="contribution_appealed",
        payload={
            "dispute_id": dispute.id,
            "parent_dispute_id": parent.id,
            "appellant_entity_id": appellant_entity_id,
            "reason": reason,
        },
    )
    db.flush()
    return dispute


def resolve_open_disputes(
    db: Session,
    contribution: ContributionEvent,
    *,
    resolver_entity_id: str,
    upheld: bool,
    note: str | None = None,
) -> list[ContributionDispute]:
    """Close open challenge/appeal after human finalization."""
    open_rows = (
        db.query(ContributionDispute)
        .filter(
            ContributionDispute.contribution_id == contribution.id,
            ContributionDispute.status == DisputeStatus.open,
        )
        .all()
    )
    if not open_rows:
        return []

    new_status = DisputeStatus.upheld if upheld else DisputeStatus.dismissed
    now = datetime.utcnow()
    for row in open_rows:
        row.status = new_status
        row.resolution_entity_id = resolver_entity_id
        row.resolution_note = note
        row.resolved_at = now

    append_ledger_record(
        db,
        contribution_id=contribution.id,
        event_type="contribution_dispute_resolved",
        payload={
            "resolver_entity_id": resolver_entity_id,
            "upheld": upheld,
            "note": note,
            "dispute_ids": [row.id for row in open_rows],
        },
    )
    db.flush()
    return open_rows


def dispute_evidence_digest(evidence: dict) -> str:
    return hashlib.sha256(
        json.dumps(evidence, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
