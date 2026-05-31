"""Import external capabilities (AgentSkills, OpenClaw manifests, MCP, agents) into PoCP entities."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy.orm import Session

from models.agent import Agent
from models.entity import Entity, EntityStatus, EntityType
from models.skill import Skill

CONFIG_DIR = Path(__file__).resolve().parents[1] / "config"
SOURCES_PATH = CONFIG_DIR / "capability_sources.yaml"
BUNDLED_DIR = CONFIG_DIR / "capabilities" / "bundled"

_FRONTMATTER = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)


def load_capability_sources() -> dict[str, Any]:
    with SOURCES_PATH.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def list_capability_sources() -> list[dict[str, Any]]:
    data = load_capability_sources()
    items: list[dict[str, Any]] = []
    for slug, spec in (data.get("sources") or {}).items():
        items.append({"slug": slug, **spec})
    return items


def capability_source_key(source: str, external_id: str) -> str:
    return f"{source}:{external_id}"


def parse_skill_md(content: str) -> dict[str, Any]:
    """Parse AgentSkills-compatible SKILL.md into metadata + instructions."""
    text = content.strip()
    match = _FRONTMATTER.match(text)
    if not match:
        raise ValueError("SKILL.md must start with YAML frontmatter between --- markers")

    frontmatter = yaml.safe_load(match.group(1)) or {}
    instructions = match.group(2).strip()
    if not isinstance(frontmatter, dict):
        raise ValueError("SKILL.md frontmatter must be a YAML mapping")

    name = frontmatter.get("name")
    if not name or not isinstance(name, str):
        raise ValueError("SKILL.md frontmatter requires string field: name")

    description = frontmatter.get("description")
    if description is not None and not isinstance(description, str):
        raise ValueError("SKILL.md description must be a string")

    return {
        "name": name.strip(),
        "description": (description or "").strip(),
        "frontmatter": frontmatter,
        "instructions": instructions,
        "content_hash": hashlib.sha256(content.encode("utf-8")).hexdigest(),
    }


def _find_skill_entity(db: Session, source_key: str) -> Entity | None:
    for entity in db.query(Entity).filter(Entity.entity_type == EntityType.skill).all():
        meta = entity.metadata_ or {}
        if meta.get("capability_source_key") == source_key:
            return entity
    return None


def _find_agent_entity(db: Session, source_key: str) -> Entity | None:
    for entity in db.query(Entity).filter(Entity.entity_type == EntityType.agent).all():
        meta = entity.metadata_ or {}
        if meta.get("capability_source_key") == source_key:
            return entity
    return None


def _resolve_import_status(source: str, *, activate: bool | None) -> EntityStatus:
    data = load_capability_sources()
    source_spec = (data.get("sources") or {}).get(source) or {}
    policy = data.get("import_policy") or {}

    if activate is True:
        return EntityStatus.active
    if activate is False:
        return EntityStatus.pending
    if source_spec.get("auto_activate") or policy.get("default_status") == "active":
        return EntityStatus.active
    return EntityStatus.pending


def import_skill_from_skill_md(
    db: Session,
    *,
    source: str,
    skill_md: str,
    external_id: str | None = None,
    maintainer_id: str,
    version: str = "1.0.0",
    runtime: dict[str, Any] | None = None,
    activate: bool | None = None,
) -> dict[str, Any]:
    parsed = parse_skill_md(skill_md)
    ext_id = (external_id or parsed["name"]).strip()
    source_key = capability_source_key(source, ext_id)
    status = _resolve_import_status(source, activate=activate)

    entity = _find_skill_entity(db, source_key)
    metadata = {
        "capability_source": source,
        "capability_source_key": source_key,
        "capability_external_id": ext_id,
        "agentskills_compat": True,
        "skill_md_hash": parsed["content_hash"],
        "frontmatter": parsed["frontmatter"],
        "runtime": runtime or {},
        "imported_via": "capability_import",
    }

    if entity is None:
        entity = Entity(
            entity_type=EntityType.skill,
            name=parsed["name"],
            description=parsed["description"] or f"Imported {source} skill: {ext_id}",
            owner_id=maintainer_id,
            creator_id=maintainer_id,
            status=status,
            metadata_=metadata,
        )
        db.add(entity)
        db.flush()
        skill = Skill(
            entity_id=entity.id,
            version=version,
            prompt_template=parsed["instructions"],
            maintainer_id=maintainer_id,
        )
        db.add(skill)
        created = True
    else:
        entity.name = parsed["name"]
        entity.description = parsed["description"] or entity.description
        entity.status = status
        entity.metadata_ = {**(entity.metadata_ or {}), **metadata}
        skill = db.query(Skill).filter(Skill.entity_id == entity.id).first()
        if skill is None:
            skill = Skill(
                entity_id=entity.id,
                version=version,
                prompt_template=parsed["instructions"],
                maintainer_id=maintainer_id,
            )
            db.add(skill)
        else:
            skill.version = version
            skill.prompt_template = parsed["instructions"]
            skill.maintainer_id = maintainer_id
        created = False

    db.flush()
    return {
        "created": created,
        "entity_id": entity.id,
        "entity_type": entity.entity_type.value,
        "name": entity.name,
        "status": entity.status.value,
        "capability_source_key": source_key,
        "skill_id": skill.id,
    }


def import_agent_manifest(
    db: Session,
    *,
    source: str,
    external_id: str,
    name: str,
    description: str | None,
    maintainer_id: str,
    capabilities: list[str] | None = None,
    service_endpoints: dict[str, str] | None = None,
    runtime: dict[str, Any] | None = None,
    activate: bool | None = None,
) -> dict[str, Any]:
    source_key = capability_source_key(source, external_id)
    status = _resolve_import_status(source, activate=activate)
    caps = capabilities or []
    endpoints = service_endpoints or {}

    entity = _find_agent_entity(db, source_key)
    metadata = {
        "capability_source": source,
        "capability_source_key": source_key,
        "capability_external_id": external_id,
        "capabilities": caps,
        "service_endpoints": endpoints,
        "runtime": runtime or {},
        "registry_compat": "capability-import-v0",
        "imported_via": "capability_import",
    }

    if entity is None:
        entity = Entity(
            entity_type=EntityType.agent,
            name=name,
            description=description,
            owner_id=maintainer_id,
            creator_id=maintainer_id,
            status=status,
            metadata_=metadata,
        )
        db.add(entity)
        db.flush()
        agent = Agent(
            entity_id=entity.id,
            config={"capabilities": caps, "service_endpoints": endpoints, "runtime": runtime or {}},
            maintainer_id=maintainer_id,
        )
        db.add(agent)
        created = True
    else:
        entity.name = name
        entity.description = description
        entity.status = status
        entity.metadata_ = {**(entity.metadata_ or {}), **metadata}
        agent = db.query(Agent).filter(Agent.entity_id == entity.id).first()
        if agent is None:
            agent = Agent(
                entity_id=entity.id,
                config={"capabilities": caps, "service_endpoints": endpoints, "runtime": runtime or {}},
                maintainer_id=maintainer_id,
            )
            db.add(agent)
        else:
            agent.config = {
                **(agent.config or {}),
                "capabilities": caps,
                "service_endpoints": endpoints,
                "runtime": runtime or {},
            }
            agent.maintainer_id = maintainer_id
        created = False

    db.flush()
    return {
        "created": created,
        "entity_id": entity.id,
        "entity_type": entity.entity_type.value,
        "name": entity.name,
        "status": entity.status.value,
        "capability_source_key": source_key,
        "agent_id": agent.id,
    }


def bind_runtime(
    db: Session,
    *,
    entity_id: str,
    runtime: dict[str, Any],
) -> Entity:
    entity = db.get(Entity, entity_id)
    if not entity:
        raise ValueError("Entity not found")
    if entity.entity_type not in (EntityType.skill, EntityType.agent, EntityType.tool):
        raise ValueError("Runtime binding applies to skill, agent, or tool entities only")

    meta = dict(entity.metadata_ or {})
    meta["runtime"] = {**(meta.get("runtime") or {}), **runtime}
    entity.metadata_ = meta

    if entity.entity_type == EntityType.agent:
        agent = db.query(Agent).filter(Agent.entity_id == entity.id).first()
        if agent:
            cfg = dict(agent.config or {})
            cfg["runtime"] = meta["runtime"]
            agent.config = cfg

    db.flush()
    return entity


def activate_capability(db: Session, entity_id: str) -> Entity:
    entity = db.get(Entity, entity_id)
    if not entity:
        raise ValueError("Entity not found")
    entity.status = EntityStatus.active
    db.flush()
    return entity


def list_capability_catalog(
    db: Session,
    *,
    source: str | None = None,
    entity_type: str | None = None,
    status: str | None = None,
) -> list[dict[str, Any]]:
    query = db.query(Entity).filter(
        Entity.entity_type.in_(
            [
                EntityType.skill,
                EntityType.agent,
                EntityType.tool,
                EntityType.llm,
                EntityType.dataset,
                EntityType.workflow,
            ]
        )
    )
    if entity_type:
        query = query.filter(Entity.entity_type == EntityType(entity_type))
    if status:
        query = query.filter(Entity.status == EntityStatus(status))

    rows: list[dict[str, Any]] = []
    for entity in query.order_by(Entity.created_at).all():
        meta = entity.metadata_ or {}
        if source and meta.get("capability_source") != source:
            continue
        rows.append(
            {
                "entity_id": entity.id,
                "entity_type": entity.entity_type.value,
                "name": entity.name,
                "description": entity.description,
                "status": entity.status.value,
                "capability_source": meta.get("capability_source"),
                "capability_source_key": meta.get("capability_source_key"),
                "capabilities": meta.get("capabilities") or [],
                "runtime": meta.get("runtime") or {},
                "service_endpoints": meta.get("service_endpoints") or {},
            }
        )
    return rows


def sync_bundled_capabilities(db: Session, *, maintainer_id: str | None = None) -> list[dict[str, Any]]:
    """Idempotently import bundled SKILL.md examples from config/capabilities/bundled/."""
    if not BUNDLED_DIR.is_dir():
        return []

    org = db.query(Entity).filter(Entity.name == "PoCP AI Commons").first()
    owner = maintainer_id or (org.id if org else None)
    if not owner:
        return []

    results: list[dict[str, Any]] = []
    for skill_dir in sorted(BUNDLED_DIR.iterdir()):
        if not skill_dir.is_dir():
            continue
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.is_file():
            continue
        result = import_skill_from_skill_md(
            db,
            source="openclaw",
            skill_md=skill_md.read_text(encoding="utf-8"),
            external_id=skill_dir.name,
            maintainer_id=owner,
            activate=True,
        )
        results.append(result)
    return results
