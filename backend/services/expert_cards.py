"""Resolve provenance human_experts_cited into Expert Cards.

Inspired by dannwaneri/proof-of-contribution — AI artifacts should point to human experts.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from models.entity import Entity
from models.wallet import ReputationScore
from services.entity_portable import find_entity_by_portable_id, resolve_or_create_portable_entity
from services.provenance import provenance_from_evidence


def _reputation_total(db: Session, entity_id: str) -> float:
    rows = db.query(ReputationScore).filter(ReputationScore.entity_id == entity_id).all()
    return round(sum(row.score for row in rows), 2)


def build_expert_card(db: Session, portable_id: str, *, create_if_missing: bool = False) -> dict:
    entity = find_entity_by_portable_id(db, portable_id)
    if entity is None and create_if_missing:
        entity = resolve_or_create_portable_entity(db, portable_id)

    card = {
        "portable_id": portable_id,
        "resolved": entity is not None,
        "entity_id": entity.id if entity else None,
        "name": entity.name if entity else portable_id.split(":")[-1],
        "entity_type": entity.entity_type.value if entity else None,
        "description": entity.description if entity else None,
        "reputation_total": _reputation_total(db, entity.id) if entity else 0.0,
        "metadata": (entity.metadata_ or {}) if entity else {},
    }
    return card


def expert_cards_from_contribution(db: Session, contribution, *, create_if_missing: bool = False) -> list[dict]:
    envelope = provenance_from_evidence(contribution.evidence) or {}
    cited = envelope.get("human_experts_cited") or []
    cards: list[dict] = []
    seen: set[str] = set()
    for portable_id in cited:
        pid = str(portable_id).strip()
        if not pid or pid in seen:
            continue
        seen.add(pid)
        cards.append(build_expert_card(db, pid, create_if_missing=create_if_missing))
    return cards


def expert_cards_from_portable_ids(
    db: Session,
    portable_ids: list[str],
    *,
    create_if_missing: bool = False,
) -> list[dict]:
    return [
        build_expert_card(db, pid, create_if_missing=create_if_missing)
        for pid in portable_ids
        if str(pid).strip()
    ]
