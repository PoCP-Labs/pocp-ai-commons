"""Sync open-source project registries into PoCP Entity rows."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from sqlalchemy.orm import Session

from models.entity import Entity, EntityStatus, EntityType
from services.neural_network_registry import load_neural_network_sources
from services.org_foundation import POCP_ORG_NAME

_OSS_COMMUNITY_PATH = Path(__file__).resolve().parents[1] / "config" / "oss_community_entities.yaml"

_CATEGORY_ENTITY_TYPE: dict[str, EntityType] = {
    "llm_inference": EntityType.llm,
    "embeddings": EntityType.tool,
    "agent_runtime": EntityType.workflow,
    "graph_ml": EntityType.tool,
    "training": EntityType.tool,
}

_STATUS_ENTITY: dict[str, EntityStatus] = {
    "active": EntityStatus.active,
    "evaluating": EntityStatus.active,
    "adapter_planned": EntityStatus.pending,
    "declined": EntityStatus.inactive,
}


def _pocp_org_entity(db: Session) -> Entity | None:
    return db.query(Entity).filter(Entity.name == POCP_ORG_NAME).first()


def _default_neural_entity_id(slug: str) -> str:
    return f"pocp-oss-nn-{slug.replace('_', '-')}"


def _parse_entity_type(raw: str | None, *, fallback: EntityType) -> EntityType:
    if not raw:
        return fallback
    try:
        return EntityType(raw)
    except ValueError:
        return fallback


def load_oss_community_registry() -> dict[str, Any]:
    if not _OSS_COMMUNITY_PATH.is_file():
        return {"spec_version": "0.1", "entities": {}}
    with _OSS_COMMUNITY_PATH.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def list_oss_entity_specs() -> list[dict[str, Any]]:
    """Merged view of neural-network sources + oss_community_entities."""
    rows: list[dict[str, Any]] = []
    nn = load_neural_network_sources()
    for slug, spec in (nn.get("sources") or {}).items():
        if not isinstance(spec, dict):
            continue
        category = spec.get("category") or "tool"
        rows.append(
            {
                "slug": slug,
                "registry": "neural_network_sources",
                "entity_id": spec.get("entity_id") or _default_neural_entity_id(slug),
                "entity_type": _parse_entity_type(
                    spec.get("entity_type"),
                    fallback=_CATEGORY_ENTITY_TYPE.get(category, EntityType.community),
                ).value,
                "display_name": spec.get("display_name", slug),
                "description": spec.get("notes") or spec.get("display_name", slug),
                "github_url": spec.get("github_url"),
                "portable_id": spec.get("portable_id") or (
                    f"github:{spec['github_url'].split('github.com/')[-1].rstrip('/')}"
                    if spec.get("github_url") and "github.com/" in spec["github_url"]
                    else None
                ),
                "category": category,
                "integration_status": spec.get("status"),
                "license": spec.get("license"),
                "pocp_modules": spec.get("pocp_modules") or [],
            }
        )
    community = load_oss_community_registry()
    for slug, spec in (community.get("entities") or {}).items():
        if not isinstance(spec, dict):
            continue
        rows.append(
            {
                "slug": slug,
                "registry": "oss_community_entities",
                "entity_id": spec.get("entity_id") or f"pocp-oss-{slug.replace('_', '-')}",
                "entity_type": spec.get("entity_type") or "community",
                "display_name": spec.get("display_name", slug),
                "description": spec.get("summary") or spec.get("display_name", slug),
                "github_url": spec.get("github_url"),
                "portable_id": spec.get("portable_id"),
                "integration_status": spec.get("status", "active"),
            }
        )
    rows.sort(key=lambda r: (r.get("registry", ""), r.get("display_name", "")))
    return rows


def ensure_neural_network_entities(db: Session) -> list[Entity]:
    """Create/update Entity rows for each entry in neural_network_sources.yaml."""
    data = load_neural_network_sources()
    org = _pocp_org_entity(db)
    touched: list[Entity] = []

    for slug, spec in (data.get("sources") or {}).items():
        if not isinstance(spec, dict):
            continue
        entity_id = spec.get("entity_id") or _default_neural_entity_id(slug)
        category = spec.get("category") or "tool"
        entity_type = _parse_entity_type(
            spec.get("entity_type"),
            fallback=_CATEGORY_ENTITY_TYPE.get(category, EntityType.community),
        )
        status = _STATUS_ENTITY.get(str(spec.get("status") or "active"), EntityStatus.active)
        metadata = {
            "oss_slug": slug,
            "registry": "neural_network_sources.yaml",
            "category": category,
            "github_url": spec.get("github_url"),
            "license": spec.get("license"),
            "integration_status": spec.get("status"),
            "integration_round": spec.get("integration_round"),
            "pocp_modules": spec.get("pocp_modules") or [],
            "portable_id": spec.get("portable_id"),
            "roles": ["open_source_compute", "neural_network_source"],
        }
        if spec.get("github_url") and not metadata["portable_id"]:
            metadata["portable_id"] = f"github:{spec['github_url'].split('github.com/')[-1].rstrip('/')}"

        entity = db.get(Entity, entity_id)
        if entity is None:
            entity = Entity(
                id=entity_id,
                entity_type=entity_type,
                name=spec.get("display_name", slug),
                description=(spec.get("notes") or "")[:500] or None,
                status=status,
                metadata_=metadata,
            )
            db.add(entity)
        else:
            entity.entity_type = entity_type
            entity.name = spec.get("display_name", slug)
            entity.description = (spec.get("notes") or entity.description or "")[:500]
            entity.status = status
            entity.metadata_ = {**(entity.metadata_ or {}), **metadata}
        if org is not None:
            entity.creator_id = org.id
        touched.append(entity)

    db.flush()
    return touched


def ensure_oss_community_entities(db: Session) -> list[Entity]:
    """Create/update Entity rows from oss_community_entities.yaml."""
    data = load_oss_community_registry()
    org = _pocp_org_entity(db)
    touched: list[Entity] = []

    for slug, spec in (data.get("entities") or {}).items():
        if not isinstance(spec, dict):
            continue
        entity_id = spec.get("entity_id") or f"pocp-oss-{slug.replace('_', '-')}"
        entity_type = _parse_entity_type(spec.get("entity_type"), fallback=EntityType.community)
        status = _STATUS_ENTITY.get(str(spec.get("status") or "active"), EntityStatus.active)
        metadata = {
            "oss_slug": slug,
            "registry": "oss_community_entities.yaml",
            "github_url": spec.get("github_url"),
            "homepage_url": spec.get("homepage_url"),
            "portable_id": spec.get("portable_id"),
            "integration_status": spec.get("status"),
            "relationship": data.get("relationship_default", "open_source_integration"),
            "roles": ["open_source_community"],
        }
        entity = db.get(Entity, entity_id)
        if entity is None:
            entity = Entity(
                id=entity_id,
                entity_type=entity_type,
                name=spec.get("display_name", slug),
                description=(spec.get("summary") or "")[:500] or None,
                status=status,
                metadata_=metadata,
            )
            db.add(entity)
        else:
            entity.entity_type = entity_type
            entity.name = spec.get("display_name", slug)
            entity.description = (spec.get("summary") or entity.description or "")[:500]
            entity.status = status
            entity.metadata_ = {**(entity.metadata_ or {}), **metadata}
        if org is not None:
            entity.creator_id = org.id
        touched.append(entity)

    db.flush()
    return touched


def ensure_all_oss_entities(db: Session) -> dict[str, int]:
    """Sync all OSS registries into Entity table."""
    nn = ensure_neural_network_entities(db)
    community = ensure_oss_community_entities(db)
    return {
        "neural_network_entities": len(nn),
        "community_entities": len(community),
        "total": len(nn) + len(community),
    }


def append_oss_entity_graph_edges(
    db: Session,
    *,
    edges: list[dict],
    entity_map: dict[str, Entity],
    append_edge,
) -> None:
    """Link PoCP org to integrated OSS entities in the contribution graph."""
    org = _pocp_org_entity(db)
    if org is None:
        return
    for spec in list_oss_entity_specs():
        entity_id = spec.get("entity_id")
        if not entity_id or entity_id not in entity_map:
            continue
        if spec.get("integration_status") in ("declined",):
            continue
        append_edge(
            edges,
            {
                "source": org.id,
                "target": entity_id,
                "relation": "integrates",
                "contribution_id": None,
                "weight": 1.0 if spec.get("integration_status") == "active" else 0.5,
            },
        )
