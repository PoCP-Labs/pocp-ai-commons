"""Clarion-0 reviewer assistant service.

Clarion-0 prepares advisory review packets for human reviewers. It never changes
contribution status and never grants approval.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from models.contribution import ContributionEvent
from models.entity import Entity
from services.evidence import POCP_META_KEY, evidence_types, standardize_evidence_items


CLARION_AGENT_ID = "pocp-entity-clarion-0"
CLARION_PACKET_VERSION = "0.1"


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def _flatten_evidence(evidence: dict | None) -> list[str]:
    if not evidence:
        return []

    items: list[str] = []
    for key, value in evidence.items():
        if key == POCP_META_KEY and isinstance(value, dict):
            content_hash = value.get("content_hash")
            if content_hash:
                items.append(f"content_hash: {content_hash}")
            continue
        if isinstance(value, list):
            visible = [str(v) for v in value if v]
            if visible:
                items.append(f"{key}: {', '.join(visible[:5])}")
        elif isinstance(value, dict):
            visible = [f"{k}={v}" for k, v in value.items() if v]
            if visible:
                items.append(f"{key}: {', '.join(visible[:5])}")
        elif value:
            items.append(f"{key}: {value}")
    return items


def _score_evidence(evidence: dict | None) -> float:
    items = _flatten_evidence(evidence)
    if not items:
        return 0.15

    score = 0.35 + min(len(items) * 0.12, 0.35)
    strong_types = {"url", "commit", "pull_request", "artifact", "content_preview", "screenshot"}
    if set(evidence_types(evidence)) & strong_types:
        score += 0.15
    meta = (evidence or {}).get(POCP_META_KEY)
    if isinstance(meta, dict) and meta.get("content_hash"):
        score += 0.10
    return round(min(score, 0.95), 4)


def _score_task_match(task_description: str, contribution_description: str) -> float:
    if not task_description:
        return 0.65 if contribution_description else 0.35
    task_terms = {t.lower().strip(".,:;()[]") for t in task_description.split() if len(t) > 3}
    contribution_terms = {
        t.lower().strip(".,:;()[]") for t in contribution_description.split() if len(t) > 3
    }
    if not task_terms or not contribution_terms:
        return 0.45
    overlap = len(task_terms & contribution_terms) / max(len(task_terms), 1)
    return round(min(0.45 + overlap * 1.2, 0.95), 4)


def _participant_summary(db: Session, contribution: ContributionEvent) -> list[dict]:
    ids = [p.entity_id for p in contribution.participants]
    entities = {e.id: e for e in db.query(Entity).filter(Entity.id.in_(ids)).all()} if ids else {}
    return [
        {
            "entity_id": p.entity_id,
            "name": entities[p.entity_id].name if p.entity_id in entities else None,
            "entity_type": entities[p.entity_id].entity_type.value if p.entity_id in entities else None,
            "role": p.role.value,
            "weight": p.weight,
            "evidence": p.evidence or {},
        }
        for p in contribution.participants
    ]


def build_clarion_review_packet(db: Session, contribution: ContributionEvent) -> dict:
    """Build an advisory packet for human review without mutating the database."""
    task = contribution.task
    task_title = _text(getattr(task, "title", ""))
    task_description = _text(getattr(task, "description", ""))
    contribution_description = _text(contribution.description)
    evidence = contribution.evidence or {}
    evidence_items = _flatten_evidence(evidence)
    standard_evidence_items = standardize_evidence_items(evidence)
    evidence_meta = evidence.get(POCP_META_KEY) if isinstance(evidence.get(POCP_META_KEY), dict) else {}
    participants = _participant_summary(db, contribution)

    evidence_score = _score_evidence(evidence)
    task_match = _score_task_match(f"{task_title} {task_description}", contribution_description)
    quality = round(min(0.45 + min(len(contribution_description) / 600, 0.35) + evidence_score * 0.2, 0.92), 4)
    originality = 0.55
    impact = round(0.55 + (0.15 if task_title else 0.0) + min(len(participants) * 0.03, 0.15), 4)

    concerns: list[str] = []
    reviewer_questions: list[str] = []

    if evidence_score < 0.5:
        concerns.append("Evidence is weak or too sparse for confident approval.")
        reviewer_questions.append("Can the contributor provide a link, artifact, commit, screenshot, or content excerpt?")
    if task_match < 0.6:
        concerns.append("Task alignment is unclear from the current description.")
        reviewer_questions.append("Which acceptance criteria does this contribution satisfy?")
    if not contribution_description:
        concerns.append("Contribution description is missing.")
        reviewer_questions.append("What exactly changed or was created?")

    creator_ids = {p["entity_id"] for p in participants if p["role"] in {"creator", "executor"}}
    reviewer_ids = {p["entity_id"] for p in participants if p["role"] == "reviewer"}
    if creator_ids & reviewer_ids:
        concerns.append("A participant appears as both contributor and reviewer; human self-approval must be blocked.")
        reviewer_questions.append("Is there an independent human reviewer available?")

    risk_score = 0.15 + (0.25 if evidence_score < 0.5 else 0.0) + (0.20 if task_match < 0.6 else 0.0)
    risk_score = round(min(risk_score, 0.95), 4)
    avg_score = round((task_match + quality + originality + impact + evidence_score) / 5, 4)

    suggested_cp = round(avg_score * 25 * (1 - min(risk_score, 0.8) * 0.35), 2)
    suggested_credits = round(avg_score * 100 * (1 - min(risk_score, 0.8) * 0.35), 2)
    recommended_status = "ready_for_human_review" if avg_score >= 0.7 and risk_score <= 0.45 else "request_changes"

    return {
        "schema_version": CLARION_PACKET_VERSION,
        "review_packet_type": "clarion_advisory_review",
        "decision_boundary": "advisory_only_human_final_approval",
        "agent": {
            "id": CLARION_AGENT_ID,
            "name": "Clarion-0",
            "role": "Reviewer Assistant / Contribution Verifier Agent",
            "decision_boundary": "advisory_only_human_final_approval",
        },
        "contribution": {
            "id": contribution.id,
            "status": contribution.status.value,
            "task_id": contribution.task_id,
            "primary_entity_id": contribution.primary_entity_id,
            "contribution_type": contribution.contribution_type,
        },
        "contribution_id": contribution.id,
        "status": contribution.status.value,
        "summary": {
            "task": task_title,
            "contribution": contribution_description or "No contribution description provided.",
            "evidence_items": evidence_items,
            "participants": participants,
        },
        "evidence": {
            "standard_version": evidence_meta.get("evidence_standard", "0.1"),
            "content_hash": evidence_meta.get("content_hash"),
            "types": evidence_types(evidence),
            "items": standard_evidence_items,
            "score": evidence_score,
        },
        "rubric": {
            "task_match": task_match,
            "quality": quality,
            "originality": originality,
            "impact": impact,
            "evidence_score": evidence_score,
            "risk_score": risk_score,
            "avg_score": avg_score,
        },
        "suggested_rewards": {
            "cp": suggested_cp,
            "ai_credits": suggested_credits,
        },
        "concerns": concerns,
        "reviewer_questions": reviewer_questions,
        "proof_draft": {
            "summary": contribution_description or "Contributor submitted work for review.",
            "evidence": evidence_items,
            "evidence_items": standard_evidence_items,
            "participants": [
                {
                    "entity_id": p["entity_id"],
                    "name": p["name"],
                    "role": p["role"],
                    "weight": p["weight"],
                }
                for p in participants
            ],
            "recommended_status": recommended_status,
            "human_review_required": True,
        },
    }
