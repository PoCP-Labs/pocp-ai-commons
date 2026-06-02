"""Idempotent platform capability registry bootstrap (PA-1)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from models.capability import EntityCapability
from models.entity import Entity
from services.capability.registry import register_capability
from services.capability.seeds import (
    CAPABILITY_SEEDS,
    R_DOCS_TOOL_ID,
    REGISTRY_MIN_COUNT,
    SKILL_CAPABILITY_ID,
    expected_capability_ids,
)
from services.entity_register import register_tool


def ensure_demo_tool_for_registry(db: Session, *, maintainer_id: str) -> str | None:
    """Ensure R docs tool entity exists so pocp-cap-r-docs-tool can register on --repair."""
    if db.get(Entity, R_DOCS_TOOL_ID):
        return None
    register_tool(
        db,
        entity_id=R_DOCS_TOOL_ID,
        name="R Docs MCP Tool",
        description="MCP tool for R documentation lookup during study note authoring",
        maintainer_id=maintainer_id,
        tool_kind="mcp",
        mcp_server="r-docs",
        capabilities=["lookup", "cite"],
        service_endpoints={"docs": "https://cran.r-project.org/manuals.html"},
    )
    return R_DOCS_TOOL_ID


def ensure_capability_registry(db: Session) -> list[str]:
    """Register seeded capabilities when backing entities exist."""
    created: list[str] = []
    for spec in CAPABILITY_SEEDS:
        cap_id = spec["capability_id"]
        if db.get(EntityCapability, cap_id):
            continue
        if db.get(Entity, spec["entity_id"]) is None:
            continue
        register_capability(
            db,
            capability_id=cap_id,
            entity_id=spec["entity_id"],
            capability_type=spec["capability_type"],
            name=spec["name"],
            unit=spec["unit"],
            price_model=spec.get("price_model", "fixed"),
            base_price=spec.get("base_price", 0.0),
            accepted_units=spec.get("accepted_units"),
            verification_method=spec.get("verification_method", "human_review"),
            metadata=spec.get("metadata"),
        )
        created.append(cap_id)
    return created


def ensure_skill_capability(db: Session, *, rain_id: str) -> list[str]:
    """Register capability for R-Tutor skill when the entity exists."""
    created: list[str] = []
    skill = db.query(Entity).filter(Entity.name == "R-Tutor Skill").first()
    if skill is None:
        return created
    if db.get(EntityCapability, SKILL_CAPABILITY_ID):
        return created
    if not skill.owner_id:
        skill.owner_id = rain_id
        skill.creator_id = skill.creator_id or rain_id
    register_capability(
        db,
        capability_id=SKILL_CAPABILITY_ID,
        entity_id=skill.id,
        capability_type="coding",
        name="R tutoring and code structure",
        unit="skill_invocation",
        verification_method="human_review",
        metadata={"language": "R", "demo": True},
    )
    created.append(SKILL_CAPABILITY_ID)
    return created


def audit_registry(db: Session) -> dict[str, Any]:
    """Capability-registry slice for entity catalog audit."""
    registered = {row.id for row in db.query(EntityCapability.id).all()}
    expected = expected_capability_ids(include_skill=True)
    missing = [cap_id for cap_id in expected if cap_id not in registered]
    count = db.query(EntityCapability).count()
    return {
        "capability_count": count,
        "missing_capabilities": missing,
        "registry_min_count": REGISTRY_MIN_COUNT,
        "registry_complete": count >= REGISTRY_MIN_COUNT and not missing,
    }


def seed_platform_capabilities(db: Session, *, rain_id: str, maintainer_id: str) -> list[str]:
    """Demo tool + catalog seeds — call after infrastructure entities exist."""
    created: list[str] = []
    tool = ensure_demo_tool_for_registry(db, maintainer_id=maintainer_id)
    if tool:
        created.append(tool)
    created.extend(ensure_capability_registry(db))
    created.extend(ensure_skill_capability(db, rain_id=rain_id))
    return created
