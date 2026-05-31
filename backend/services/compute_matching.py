"""Complementary compute provider matching — Phase γ."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from models.entity import Entity
from models.task import Task
from services.compute_profile import list_compute_provider_entities
from services.compute_reputation import load_compute_provider_reputation_map

CAPABILITY_KEYWORDS: dict[str, set[str]] = {
    "llm_inference": {
        "research",
        "writing",
        "code",
        "analysis",
        "paper",
        "skill",
        "agent",
        "llm",
        "draft",
        "matrix",
        "document",
    },
    "witness": {
        "verify",
        "verification",
        "audit",
        "review",
        "pilot",
        "witness",
        "consensus",
        "proof",
    },
    "embeddings": {"semantic", "dedup", "similarity", "match", "embedding", "vector"},
    "mcp_host": {"tool", "api", "integration", "mcp", "workflow", "invoke"},
    "agent_runtime": {"agent", "multi", "study", "runtime", "orchestr", "step"},
}

DEFAULT_CAPABILITIES = ("llm_inference", "witness")


def _task_keywords(task: Task | None) -> set[str]:
    if not task:
        return set()
    text = f"{task.title} {task.description or ''}".lower()
    return {word for word in text.replace(",", " ").split() if len(word) > 2}


def _contribution_type_keywords(contribution_type: str | None) -> set[str]:
    if not contribution_type:
        return set()
    return {w for w in contribution_type.replace("_", " ").lower().split() if len(w) > 2}


def infer_required_capabilities(
    *,
    task_keywords: set[str],
    contribution_type: str | None,
) -> list[dict[str, Any]]:
    """Score capabilities by keyword overlap with task / contribution type."""
    pool = task_keywords | _contribution_type_keywords(contribution_type)
    scored: list[tuple[str, float]] = []
    for capability, hints in CAPABILITY_KEYWORDS.items():
        if not pool:
            score = 0.5 if capability in DEFAULT_CAPABILITIES else 0.0
        else:
            hits = sum(1 for token in pool if token in hints or any(h in token for h in hints))
            score = min(1.0, hits / max(len(pool), 1))
        if score > 0:
            scored.append((capability, round(score, 3)))

    scored.sort(key=lambda item: item[1], reverse=True)
    if not scored:
        return [{"capability": cap, "need_score": 0.5} for cap in DEFAULT_CAPABILITIES]

    top = [item for item in scored if item[1] >= 0.15][:4]
    return [{"capability": cap, "need_score": score} for cap, score in top]


def recommend_compute_providers(
    db: Session,
    *,
    task_id: str | None = None,
    contribution_type: str | None = None,
    initiator_entity_id: str | None = None,
    limit_per_capability: int = 3,
) -> dict[str, Any]:
    """Suggest Entity compute providers complementary to a task."""
    task = db.query(Task).filter(Task.id == task_id).first() if task_id else None
    task_keywords = _task_keywords(task)
    required = infer_required_capabilities(
        task_keywords=task_keywords,
        contribution_type=contribution_type,
    )
    rep_map = load_compute_provider_reputation_map(db)
    max_rep = max(rep_map.values(), default=1.0) or 1.0
    initiator = db.get(Entity, initiator_entity_id) if initiator_entity_id else None

    by_capability: list[dict[str, Any]] = []
    for item in required:
        capability = item["capability"]
        providers = list_compute_provider_entities(
            db,
            capability=capability,
            status="active",
            initiator_entity_id=initiator_entity_id,
            mesh_filter=bool(initiator_entity_id),
        )
        ranked: list[dict[str, Any]] = []
        for row in providers:
            profile = row["compute_profile"]
            owner_id = (profile.get("accountability") or {}).get("owner_entity_id")
            rep = rep_map.get(row["entity_id"], 0.0)
            rep_norm = rep / max_rep
            affinity = 0.0
            if initiator:
                if row["entity_id"] == initiator.id:
                    affinity = 1.0
                elif owner_id == initiator.id:
                    affinity = 0.8
                elif initiator.owner_id and row["entity_id"] == initiator.owner_id:
                    affinity = 0.5

            offer = next(
                (o for o in profile.get("offers") or [] if o.get("capability") == capability),
                {},
            )
            models = offer.get("models") or []
            region = (profile.get("capacity") or {}).get("region") or ""
            match_score = round(
                0.45 * item["need_score"] + 0.35 * rep_norm + 0.20 * affinity,
                4,
            )
            ranked.append(
                {
                    "entity_id": row["entity_id"],
                    "name": row["name"],
                    "entity_type": row["entity_type"],
                    "capability": capability,
                    "models": models,
                    "region": region,
                    "compute_provider_reputation": round(rep, 2),
                    "affinity": round(affinity, 2),
                    "match_score": match_score,
                    "endpoints": profile.get("endpoints") or {},
                }
            )

        ranked.sort(key=lambda row: row["match_score"], reverse=True)
        by_capability.append(
            {
                "capability": capability,
                "need_score": item["need_score"],
                "recommended_providers": ranked[:limit_per_capability],
            }
        )

    flat = sorted(
        (
            provider
            for group in by_capability
            for provider in group["recommended_providers"]
        ),
        key=lambda row: row["match_score"],
        reverse=True,
    )[: limit_per_capability * 2]

    return {
        "task_id": task_id,
        "task_title": task.title if task else None,
        "contribution_type": contribution_type,
        "task_keywords": sorted(task_keywords),
        "required_capabilities": required,
        "by_capability": by_capability,
        "recommended_compute_providers": flat,
        "strategy": "complementary_compute_v0.1",
        "advisory_only": True,
    }
