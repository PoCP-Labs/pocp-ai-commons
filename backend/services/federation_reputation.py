"""Aggregate local and federated reputation by portable identity."""

from sqlalchemy.orm import Session

from models.federation import FederatedImport
from models.wallet import ReputationScore
from services.entity_portable import find_entity_by_portable_id


def get_federated_reputation(db: Session, portable_id: str) -> dict:
    entity = find_entity_by_portable_id(db, portable_id)
    local_scores: list[dict] = []
    if entity:
        rows = db.query(ReputationScore).filter(ReputationScore.entity_id == entity.id).all()
        local_scores = [
            {"category": row.category, "score": round(row.score, 2), "source": "local"}
            for row in rows
        ]

    imports = (
        db.query(FederatedImport)
        .filter(FederatedImport.primary_portable_id == portable_id)
        .order_by(FederatedImport.imported_at.desc())
        .all()
    )
    federated_total = round(sum(item.reputation_applied for item in imports), 2)

    by_category: dict[str, float] = {}
    for item in local_scores:
        by_category[item["category"]] = by_category.get(item["category"], 0.0) + item["score"]
    if federated_total > 0:
        by_category["federated"] = by_category.get("federated", 0.0) + federated_total

    return {
        "portable_id": portable_id,
        "found": entity is not None,
        "entity_id": entity.id if entity else None,
        "local_reputation": local_scores,
        "federated_import_count": len(imports),
        "federated_reputation_total": federated_total,
        "aggregated_by_category": {k: round(v, 2) for k, v in by_category.items()},
        "total_score": round(sum(by_category.values()), 2),
        "recent_imports": [
            {
                "source_node_id": item.source_node_id,
                "source_contribution_id": item.source_contribution_id,
                "task_title": item.task_title,
                "reputation_applied": item.reputation_applied,
                "trust_weight": item.trust_weight,
                "imported_at": item.imported_at.isoformat(),
            }
            for item in imports[:10]
        ],
    }
