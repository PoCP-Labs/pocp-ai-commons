"""Seed demo ComputeProfile declarations on exemplar entities."""

from __future__ import annotations

import os

from sqlalchemy.orm import Session

from genesis import DESUI_ID, LUMEN_0_ID
from models.entity import Entity
from services.compute_profile import get_compute_profile, register_compute_profile

R_DOCS_TOOL_ID = "pocp-entity-r-docs-tool"


def ensure_demo_compute_profiles(
    db: Session,
    *,
    rain: Entity,
    lumen: Entity | None = None,
    desui: Entity | None = None,
    tool: Entity | None = None,
    org: Entity | None = None,
) -> int:
    """Idempotently attach compute_profile to demo entities. Returns count updated."""
    backend = os.getenv("BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")
    node_id = os.getenv("POCP_NODE_ID", "pocp-node-local")

    lumen = lumen or db.get(Entity, LUMEN_0_ID)
    desui = desui or db.get(Entity, DESUI_ID)
    tool = tool or db.get(Entity, R_DOCS_TOOL_ID)

    specs: list[tuple[Entity | None, dict]] = [
        (
            lumen,
            {
                "offers": [
                    {
                        "capability": "witness",
                        "adapters": ["mock", "ollama", "llama_cpp"],
                        "models": ["Lumen-0"],
                    }
                ],
                "endpoints": {
                    "base_url": backend,
                    "witness": "/api/v1/intelligence/compute/witness",
                    "status": "/api/v1/intelligence/compute/status",
                },
                "capacity": {"max_concurrent": 2, "region": "genesis"},
                "accountability": {"owner_entity_id": org.id if org else rain.id},
                "policy": {
                    "accepts_public_jobs": True,
                    "visibility": "trusted_federation",
                    "trusted_node_ids": [node_id],
                    "organization_entity_id": org.id if org else None,
                },
                "status": "active",
            },
        ),
        (
            desui,
            {
                "offers": [
                    {
                        "capability": "witness",
                        "adapters": ["mock", "deepseek"],
                        "models": ["DeSui"],
                    }
                ],
                "endpoints": {"base_url": backend},
                "capacity": {"max_concurrent": 2, "region": "genesis"},
                "accountability": {"owner_entity_id": org.id if org else rain.id},
                "policy": {
                    "accepts_public_jobs": True,
                    "visibility": "trusted_federation",
                    "organization_entity_id": org.id if org else None,
                },
                "status": "active",
            },
        ),
        (
            tool,
            {
                "offers": [
                    {
                        "capability": "mcp_host",
                        "tools": ["r-docs"],
                        "adapters": ["mcp"],
                    }
                ],
                "endpoints": {"base_url": backend},
                "capacity": {"max_concurrent": 4, "region": "demo"},
                "accountability": {"owner_entity_id": rain.id},
                "policy": {"accepts_public_jobs": False, "visibility": "org_only"},
                "status": "active",
            },
        ),
        (
            rain,
            {
                "offers": [
                    {
                        "capability": "llm_inference",
                        "adapters": ["mock", "ollama"],
                        "models": ["qwen2.5:7b"],
                    },
                    {"capability": "embeddings", "adapters": ["ollama"]},
                ],
                "endpoints": {"base_url": backend},
                "capacity": {"max_concurrent": 1, "region": "local"},
                "accountability": {"owner_entity_id": rain.id},
                "policy": {"accepts_public_jobs": False, "visibility": "org_only"},
                "status": "active",
            },
        ),
    ]

    updated = 0
    for entity, profile in specs:
        if entity is None:
            continue
        if get_compute_profile(entity):
            existing = get_compute_profile(entity)
            if existing and existing.get("spec_version") == "0.1":
                continue
        register_compute_profile(db, entity.id, profile, owner_entity_id=rain.id)
        updated += 1
    return updated
