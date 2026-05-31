"""Shared contribution submission — used by REST and A2A task bridge."""

from __future__ import annotations

import os
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from intelligence import capability_layer
from models.contribution import (
    ContributionEvent,
    ContributionParticipant,
    ContributionStatus,
    ParticipantRole,
)
from models.entity import Entity
from models.task import Task
from services.entity_register import validate_participants_for_submission
from services.evidence import POCP_META_KEY, enrich_evidence
from services.evidence_validate import validate_evidence_urls
from services.provenance import attach_provenance_to_evidence
from services.training_contribution import TRAINING_TYPE, enrich_training_evidence, validate_training_evidence


def submit_contribution_event(
    db: Session,
    *,
    human_entity_id: str,
    task_id: str,
    contribution_type: str = "knowledge",
    description: str | None = None,
    evidence: dict[str, Any] | None = None,
    participants: list[dict[str, Any]] | None = None,
    provenance: dict[str, Any] | None = None,
) -> ContributionEvent:
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    evidence = dict(evidence or {})
    capability_layer.precheck_submission(db, entity_id=human_entity_id, evidence=evidence)

    participant_rows = participants or []
    if participant_rows and os.getenv("POCP_VALIDATE_PARTICIPANT_ONTOLOGY", "true").lower() == "true":
        participant_ids = {p["entity_id"] for p in participant_rows}
        participant_entities = {
            e.id: e for e in db.query(Entity).filter(Entity.id.in_(participant_ids)).all()
        }
        try:
            validate_participants_for_submission(participant_rows, participant_entities)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    evidence = enrich_evidence(evidence)
    if provenance is not None:
        evidence = attach_provenance_to_evidence(
            evidence,
            declared_by_entity_id=human_entity_id,
            creation_mode=provenance.get("creation_mode", "unknown"),
            ai_tools_used=provenance.get("ai_tools_used") or [],
            human_experts_cited=provenance.get("human_experts_cited") or [],
            review_depth=provenance.get("review_depth"),
            notes=provenance.get("notes"),
            verification_claims=provenance.get("verification_claims") or [],
        )

    if os.getenv("POCP_VALIDATE_EVIDENCE_URLS", "false").lower() == "true":
        url_report = validate_evidence_urls(evidence)
        meta = dict(evidence.get(POCP_META_KEY) or {})
        meta["url_checks"] = url_report
        evidence[POCP_META_KEY] = meta

    if contribution_type.strip().lower() == TRAINING_TYPE:
        try:
            validate_training_evidence(evidence)
            evidence = enrich_training_evidence(evidence)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    contribution = ContributionEvent(
        task_id=task_id,
        primary_entity_id=human_entity_id,
        contribution_type=contribution_type,
        description=description,
        evidence=evidence,
        status=ContributionStatus.submitted,
    )
    db.add(contribution)
    db.flush()

    for p in participant_rows:
        try:
            role = ParticipantRole(p["role"])
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=f"Invalid role: {p['role']}") from exc
        db.add(
            ContributionParticipant(
                contribution_id=contribution.id,
                entity_id=p["entity_id"],
                role=role,
                weight=float(p.get("weight") or 0.0),
                evidence=p.get("evidence") or {},
            )
        )

    db.flush()
    return (
        db.query(ContributionEvent)
        .options(
            joinedload(ContributionEvent.participants),
            joinedload(ContributionEvent.ai_verifications),
            joinedload(ContributionEvent.human_reviews),
        )
        .filter(ContributionEvent.id == contribution.id)
        .first()
    )
