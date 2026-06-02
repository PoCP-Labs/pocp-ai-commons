"""Register and manage PoCP Meta engineering Agents as protocol Entities."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from meta_agents_spec import (
    META_AGENT_BY_ID,
    META_AGENT_IDS,
    META_AGENT_SPECS,
    NEXUS_ID,
    agent_config_for_spec,
    entity_metadata_for_spec,
)
from models.agent import Agent
from models.entity import Entity, EntityStatus, EntityType
from services.org_foundation import POCP_ORG_NAME

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _org_entity(db: Session) -> Entity | None:
    return db.query(Entity).filter(Entity.name == POCP_ORG_NAME).first()


def _merge_agent_config(base: dict[str, Any], existing: dict[str, Any]) -> dict[str, Any]:
    """Preserve evolved learning_profile / capabilities when re-syncing roster."""
    merged = {**base, **existing}
    base_lp = dict(base.get("learning_profile") or {})
    exist_lp = dict(existing.get("learning_profile") or {})
    merged["learning_profile"] = {**base_lp, **exist_lp}
    merged["memory_store"] = {
        **dict(base.get("memory_store") or {}),
        **dict(existing.get("memory_store") or {}),
    }
    return merged


def _load_prompt_text(spec_slug: str) -> str | None:
    path = _REPO_ROOT / "agents" / "prompts" / f"{spec_slug}.md"
    if not path.is_file():
        return None
    return path.read_text(encoding="utf-8")


def ensure_meta_agents(db: Session) -> list[str]:
    """Idempotently upsert all Meta Agent entities and Agent config (incl. prompt path)."""
    org = _org_entity(db)
    ensured: list[str] = []

    for spec in META_AGENT_SPECS:
        entity_id = spec["id"]
        entity = db.get(Entity, entity_id)
        meta = entity_metadata_for_spec(spec)
        base_config = agent_config_for_spec(spec)

        if entity is None:
            entity = Entity(
                id=entity_id,
                entity_type=EntityType.agent,
                name=spec["name"],
                description=spec["description"],
                status=EntityStatus.active,
                metadata_=meta,
            )
            db.add(entity)
        else:
            entity.name = spec["name"]
            entity.description = spec["description"]
            entity.entity_type = EntityType.agent
            entity.status = EntityStatus.active
            entity.metadata_ = meta

        if org is not None:
            entity.creator_id = org.id
            entity.owner_id = org.id

        agent = db.query(Agent).filter(Agent.entity_id == entity.id).first()
        if agent is None:
            agent = Agent(
                entity_id=entity.id,
                config=base_config,
                maintainer_id=org.id if org is not None else None,
            )
            db.add(agent)
        else:
            agent.config = _merge_agent_config(base_config, dict(agent.config or {}))
            if org is not None:
                agent.maintainer_id = org.id

        prompt_body = _load_prompt_text(spec["slug"])
        if prompt_body:
            cfg = dict(agent.config or {})
            cfg["prompt_synced"] = True
            cfg["prompt_chars"] = len(prompt_body)
            agent.config = cfg

        ensured.append(entity_id)

    db.flush()
    return ensured


def list_meta_agents(db: Session) -> list[dict[str, Any]]:
    """Return all registered Meta Agents with entity, agent config, and skill summary."""
    entities = (
        db.query(Entity)
        .filter(Entity.id.in_(META_AGENT_IDS))
        .order_by(Entity.name)
        .all()
    )
    return [_meta_agent_view(db, e) for e in entities]


def get_meta_agent(db: Session, entity_id: str) -> dict[str, Any] | None:
    if entity_id not in META_AGENT_IDS:
        return None
    entity = db.get(Entity, entity_id)
    if entity is None:
        return None
    return _meta_agent_view(db, entity)


def _meta_agent_view(db: Session, entity: Entity) -> dict[str, Any]:
    spec = META_AGENT_BY_ID.get(entity.id, {})
    agent = db.query(Agent).filter(Agent.entity_id == entity.id).first()
    meta = dict(entity.metadata_ or {})
    config = dict(agent.config or {}) if agent else {}
    profile = dict(config.get("learning_profile") or {})
    slug = meta.get("slug") or spec.get("slug") or ""
    prompt_path = config.get("prompt_path") or meta.get("prompt_path")
    prompt_loaded = _load_prompt_text(slug) if slug else None
    return {
        "entity_id": entity.id,
        "name": entity.name,
        "description": entity.description,
        "status": entity.status.value,
        "entity_type": entity.entity_type.value,
        "slug": meta.get("slug") or spec.get("slug"),
        "task_label": meta.get("task_label") or spec.get("task_label"),
        "roles": meta.get("roles") or spec.get("roles", []),
        "capabilities": meta.get("capabilities") or spec.get("capabilities", []),
        "evolved_capabilities": profile.get("evolved_capabilities", []),
        "evolution_version": profile.get("evolution_version", 0),
        "memory_store_path": profile.get("memory_store_path") or (config.get("memory_store") or {}).get("path"),
        "reports_to": meta.get("reports_to"),
        "handoff_default": meta.get("handoff_default", NEXUS_ID),
        "orchestrates": config.get("orchestrates", spec.get("orchestrates", [])),
        "writable_paths": config.get("writable_paths", spec.get("writable_paths", [])),
        "prompt_path": config.get("prompt_path"),
        "cursor_skill": config.get("cursor_skill"),
        "cursor_rule": config.get("cursor_rule"),
        "agent_config": config,
        "cursor_capabilities": {
            "prompt_path": prompt_path,
            "prompt_available": bool(prompt_loaded),
            "prompt_chars": len(prompt_loaded or ""),
            "cursor_skill": config.get("cursor_skill"),
            "cursor_rule": config.get("cursor_rule"),
        },
        "owner_id": entity.owner_id,
        "maintainer_id": agent.maintainer_id if agent else None,
    }


def meta_agent_roster_summary() -> dict[str, Any]:
    """Static roster for docs/API without DB."""
    return {
        "layer": "meta_orchestration",
        "count": len(META_AGENT_SPECS),
        "nexus_id": NEXUS_ID,
        "agents": [
            {
                "entity_id": s["id"],
                "name": s["name"],
                "task_label": s["task_label"],
                "reports_to": s["reports_to"],
            }
            for s in META_AGENT_SPECS
        ],
    }
