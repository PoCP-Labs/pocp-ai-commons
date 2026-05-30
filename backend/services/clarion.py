"""Clarion-0 reviewer assistant service.

Clarion-0 prepares advisory review packets for human reviewers. It never changes
contribution status and never grants approval.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from models.contribution import ContributionEvent
from models.entity import Entity
from services.code_attribution_bridge import build_code_attribution_context
from services.evidence import POCP_META_KEY, evidence_types, standardize_evidence_items
from services.evidence_validate import validate_evidence_full
from services.expert_cards import expert_cards_from_contribution
from services.provenance import provenance_from_evidence
from services.reward_advisory import build_reward_advisory

CLARION_AGENT_ID = "pocp-entity-clarion-0"
CLARION_PACKET_VERSION = "0.2"


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


def _compute_risk_score(evidence_score: float, task_match: float, participants: list[dict]) -> float:
    creator_ids = {p.get("entity_id") for p in participants if p.get("role") in {"creator", "executor"}}
    reviewer_ids = {p.get("entity_id") for p in participants if p.get("role") == "reviewer"}
    risk_score = 0.15 + (0.25 if evidence_score < 0.5 else 0.0) + (0.20 if task_match < 0.6 else 0.0)
    if creator_ids & reviewer_ids:
        risk_score += 0.20
    return round(min(risk_score, 0.95), 4)


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


def score_context_for_verifier(context: dict) -> dict:
    """Score a verifier context dict using Clarion heuristics (no DB required)."""
    task = context.get("task") or {}
    contribution = context.get("contribution") or {}
    task_title = _text(task.get("title"))
    task_description = _text(task.get("description"))
    contribution_description = _text(contribution.get("description"))
    evidence = contribution.get("evidence") or {}
    participants = context.get("participants") or []

    evidence_score = _score_evidence(evidence)
    task_match = _score_task_match(f"{task_title} {task_description}", contribution_description)
    quality = round(min(0.45 + min(len(contribution_description) / 600, 0.35) + evidence_score * 0.2, 0.92), 4)
    originality = 0.55
    impact = round(0.55 + (0.15 if task_title else 0.0) + min(len(participants) * 0.03, 0.15), 4)

    concerns: list[str] = []
    if evidence_score < 0.5:
        concerns.append("Evidence is weak or too sparse for confident approval.")
    if task_match < 0.6:
        concerns.append("Task alignment is unclear from the current description.")

    risk_score = _compute_risk_score(evidence_score, task_match, participants)
    avg_score = round((task_match + quality + originality + impact + evidence_score) / 5, 4)
    suggested_cp = round(avg_score * 25 * (1 - min(risk_score, 0.8) * 0.35), 2)
    suggested_credits = round(avg_score * 100 * (1 - min(risk_score, 0.8) * 0.35), 2)

    return {
        "task_match": task_match,
        "quality": quality,
        "originality": originality,
        "impact": impact,
        "evidence_score": evidence_score,
        "risk_score": risk_score,
        "avg_score": avg_score,
        "suggested_cp": suggested_cp,
        "suggested_credits": suggested_credits,
        "concerns": concerns,
        "rationale": (
            f"Clarion-0 heuristic review: avg={avg_score}, evidence={evidence_score}, "
            f"task_match={task_match}, risk={risk_score}."
        ),
    }


def _merge_ai_consensus(heuristic: dict[str, float], consensus: dict | None) -> dict[str, float]:
    if not consensus:
        return heuristic
    merged = dict(heuristic)
    mapping = {
        "task_match": "avg_task_match",
        "quality": "avg_quality",
        "originality": "avg_originality",
        "impact": "avg_impact",
        "evidence_score": "avg_evidence",
        "risk_score": "avg_risk",
        "avg_score": "avg_score",
    }
    for key, ai_key in mapping.items():
        ai_val = consensus.get(ai_key)
        if ai_val is not None and key in merged:
            merged[key] = round((merged[key] + float(ai_val)) / 2, 4)
    return merged


def build_clarion_review_packet(db: Session, contribution: ContributionEvent) -> dict:
    """Build a unified advisory packet merging heuristics, AI consensus, and integrations."""
    task = contribution.task
    task_title = _text(getattr(task, "title", ""))
    task_description = _text(getattr(task, "description", ""))
    contribution_description = _text(contribution.description)
    evidence = contribution.evidence or {}
    evidence_items = _flatten_evidence(evidence)
    standard_evidence_items = standardize_evidence_items(evidence)
    evidence_meta = evidence.get(POCP_META_KEY) if isinstance(evidence.get(POCP_META_KEY), dict) else {}
    participants = _participant_summary(db, contribution)

    heuristic = score_context_for_verifier(
        {
            "task": {"title": task_title, "description": task_description},
            "contribution": {
                "description": contribution_description,
                "evidence": evidence,
            },
            "participants": participants,
        }
    )

    reward_advisory = build_reward_advisory(db, contribution)
    consensus = reward_advisory.get("consensus")
    unified_rubric = _merge_ai_consensus(
        {
            "task_match": heuristic["task_match"],
            "quality": heuristic["quality"],
            "originality": heuristic["originality"],
            "impact": heuristic["impact"],
            "evidence_score": heuristic["evidence_score"],
            "risk_score": heuristic["risk_score"],
            "avg_score": heuristic["avg_score"],
        },
        consensus,
    )

    concerns = list(heuristic["concerns"])
    reviewer_questions: list[str] = []
    if heuristic["evidence_score"] < 0.5:
        reviewer_questions.append("Can the contributor provide a link, artifact, commit, screenshot, or content excerpt?")
    if heuristic["task_match"] < 0.6:
        reviewer_questions.append("Which acceptance criteria does this contribution satisfy?")
    if not contribution_description:
        concerns.append("Contribution description is missing.")
        reviewer_questions.append("What exactly changed or was created?")

    risk_score = unified_rubric["risk_score"]
    avg_score = unified_rubric["avg_score"]
    recommended_status = "ready_for_finalization" if avg_score >= 0.7 and risk_score <= 0.45 else "request_changes"

    suggested_cp = reward_advisory.get("recommended", {}).get("cp") or heuristic["suggested_cp"]
    suggested_credits = reward_advisory.get("recommended", {}).get("ai_credits") or heuristic["suggested_credits"]

    return {
        "schema_version": CLARION_PACKET_VERSION,
        "review_packet_type": "clarion_unified_advisory_review",
        "decision_boundary": "traceable_finalization",
        "agent": {
            "id": CLARION_AGENT_ID,
            "name": "Clarion-0",
            "role": "Reviewer Assistant / Contribution Verifier Agent",
            "decision_boundary": "traceable_finalization",
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
            "score": unified_rubric["evidence_score"],
            "provenance": provenance_from_evidence(evidence),
        },
        "rubric": unified_rubric,
        "heuristic_rubric": {
            "task_match": heuristic["task_match"],
            "quality": heuristic["quality"],
            "originality": heuristic["originality"],
            "impact": heuristic["impact"],
            "evidence_score": heuristic["evidence_score"],
            "risk_score": heuristic["risk_score"],
            "avg_score": heuristic["avg_score"],
        },
        "ai_consensus": consensus,
        "suggested_rewards": {
            "cp": suggested_cp,
            "ai_credits": suggested_credits,
            "source": "ai_consensus" if consensus else "clarion_heuristic",
        },
        "concerns": concerns,
        "reviewer_questions": reviewer_questions,
        "integrations": {
            "reward_advisory": reward_advisory,
            "expert_cards": expert_cards_from_contribution(db, contribution),
            "code_attribution": build_code_attribution_context(evidence),
            "evidence_checks": validate_evidence_full(evidence),
        },
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
            "traceable_finalization_required": True,
        },
    }
