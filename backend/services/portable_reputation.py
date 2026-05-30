"""Portable off-chain reputation bundle (TrustMyGit-inspired, no chain required)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from models.entity import Entity
from services.agent_reputation import get_agent_reputation_summary
from services.entity_portable import find_entity_by_portable_id
from services.federation_reputation import get_federated_reputation
from services.reputation_audit import list_reputation_audit


def build_portable_reputation_bundle(db: Session, entity: Entity) -> dict:
    metadata = entity.metadata_ or {}
    portable_id = metadata.get("portable_id")
    federation = (
        get_federated_reputation(db, portable_id)
        if portable_id
        else {
            "portable_id": None,
            "found": True,
            "entity_id": entity.id,
            "local_reputation": [],
            "aggregated_by_category": {},
            "total_score": 0.0,
        }
    )

    agent_summary = None
    if entity.entity_type.value == "agent":
        try:
            agent_summary = get_agent_reputation_summary(db, entity.id)
        except Exception:
            agent_summary = None

    return {
        "schema_version": "0.1",
        "bundle_type": "pocp_portable_reputation",
        "compat": ["trustmygit-offchain-v0", "erc-8004-offchain-v0"],
        "entity": {
            "id": entity.id,
            "entity_type": entity.entity_type.value,
            "name": entity.name,
            "portable_id": portable_id,
            "metadata": metadata,
        },
        "federation": federation,
        "agent_feedback": agent_summary,
        "audit_trail": list_reputation_audit(db, entity.id, limit=20),
    }


def build_portable_reputation_by_id(db: Session, entity_id: str) -> dict:
    entity = db.query(Entity).filter(Entity.id == entity_id).first()
    if not entity:
        raise ValueError("Entity not found")
    return build_portable_reputation_bundle(db, entity)


def build_portable_reputation_by_portable_id(db: Session, portable_id: str) -> dict:
    entity = find_entity_by_portable_id(db, portable_id)
    if not entity:
        raise ValueError(f"No entity found for portable_id {portable_id}")
    return build_portable_reputation_bundle(db, entity)
