"""Semantic duplicate hints for contributions (advisory; optional block via env)."""

from __future__ import annotations

import os
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from models.contribution import ContributionEvent, ContributionStatus
from services.embedding_match import cosine_similarity, embed_document, embedding_provider


def _contribution_text(contribution: ContributionEvent) -> str:
    parts = [contribution.description or "", contribution.contribution_type or ""]
    evidence = contribution.evidence or {}
    for key in ("summary", "content", "notes", "links"):
        value = evidence.get(key)
        if isinstance(value, str):
            parts.append(value)
        elif isinstance(value, list):
            parts.extend(str(v) for v in value[:5])
    return " ".join(p for p in parts if p).strip()


def semantic_dedup_threshold() -> float:
    return float(os.getenv("POCP_SEMANTIC_DEDUP_THRESHOLD", "0.88"))


def semantic_dedup_lookback_days() -> int:
    return int(os.getenv("POCP_SEMANTIC_DEDUP_LOOKBACK_DAYS", "90"))


def find_semantic_duplicates(
    db: Session,
    *,
    entity_id: str | None,
    description: str | None,
    evidence: dict | None,
    exclude_contribution_id: str | None = None,
    limit: int = 5,
) -> list[dict]:
    """Return advisory duplicate hints sorted by similarity desc."""
    if embedding_provider() is None:
        return []

    query_text = " ".join(
        p
        for p in [
            description or "",
            str((evidence or {}).get("summary") or ""),
            str((evidence or {}).get("content") or ""),
        ]
        if p
    ).strip()
    if not query_text:
        return []

    query_vec = embed_document(query_text)
    if query_vec is None:
        return []

    since = datetime.utcnow() - timedelta(days=semantic_dedup_lookback_days())
    q = db.query(ContributionEvent).filter(
        ContributionEvent.created_at >= since,
        ContributionEvent.status.in_(
            [
                ContributionStatus.submitted,
                ContributionStatus.ai_verified,
                ContributionStatus.approved,
            ]
        ),
    )
    if entity_id:
        q = q.filter(ContributionEvent.primary_entity_id == entity_id)

    threshold = semantic_dedup_threshold()
    hints: list[dict] = []
    for candidate in q.order_by(ContributionEvent.created_at.desc()).limit(200).all():
        if exclude_contribution_id and candidate.id == exclude_contribution_id:
            continue
        doc_vec = embed_document(_contribution_text(candidate))
        if doc_vec is None:
            continue
        similarity = cosine_similarity(query_vec, doc_vec)
        if similarity >= threshold:
            hints.append(
                {
                    "contribution_id": candidate.id,
                    "status": candidate.status.value,
                    "similarity": round(similarity, 4),
                    "primary_entity_id": candidate.primary_entity_id,
                    "advisory": "possible_semantic_duplicate",
                }
            )

    hints.sort(key=lambda h: h["similarity"], reverse=True)
    return hints[:limit]
