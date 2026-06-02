"""Platform entity catalog — audit, register missing types, seed capabilities, assign ownership."""

from __future__ import annotations

import os
from collections import Counter
from typing import Any

from sqlalchemy.orm import Session

from genesis import RAIN_ID
from intelligence.entity_ontology import all_entity_types
from models.entity import Entity, EntityType
from services.capability.bootstrap import audit_registry, seed_platform_capabilities
from services.capability.seeds import (  # re-exported for scripts/tests
    BOB_REVIEWER_NODE_ID,
    CAPABILITY_SEEDS,
    LOCAL_COMPUTE_NODE_ID,
    LOCAL_VERIFIER_NODE_ID,
    PROTOCOL_TREASURY_ID,
    RAIN_SPONSOR_ID,
    R_DOCS_TOOL_ID,
    STUDY_WORKFLOW_ID,
)
from services.entity_register import (
    register_compute_node,
    register_protocol_treasury,
    register_reviewer_node,
    register_sponsor_entity,
    register_verifier_node,
    register_workflow,
)
from services.node.store import get_node_by_entity, register_node

POCP_ORG_NAME = "PoCP AI Commons"

# Demo entities that should be owned by Rain when owner_id is missing.
DEMO_OWNERSHIP_BY_NAME: dict[str, str] = {
    "StudyAgent": RAIN_ID,
    "R-Tutor Skill": RAIN_ID,
    "study-notes": RAIN_ID,
    "summarize": RAIN_ID,
    "Fetch (MCP)": RAIN_ID,
    "Get Current Time (MCP)": RAIN_ID,
    "MCP Fetch (demo)": RAIN_ID,
    "MCP Time Server (demo)": RAIN_ID,
}

def _resolve_org(db: Session) -> Entity | None:
    return db.query(Entity).filter(Entity.name == POCP_ORG_NAME).first()


def _resolve_bob(db: Session) -> Entity | None:
    return db.query(Entity).filter(Entity.name == "Bob").first()


def audit_entity_catalog(db: Session) -> dict[str, Any]:
    """Summarize entity coverage, capability registry, and ownership gaps."""
    rows = db.query(Entity).all()
    by_type = Counter(e.entity_type.value for e in rows)
    ontology_types = all_entity_types()
    missing_types = [t for t in ontology_types if by_type.get(t, 0) == 0]

    registry_audit = audit_registry(db)
    cap_count = registry_audit["capability_count"]
    missing_capabilities = registry_audit["missing_capabilities"]

    missing_infrastructure = [
        eid
        for eid in (
            LOCAL_COMPUTE_NODE_ID,
            LOCAL_VERIFIER_NODE_ID,
            BOB_REVIEWER_NODE_ID,
            RAIN_SPONSOR_ID,
            PROTOCOL_TREASURY_ID,
            STUDY_WORKFLOW_ID,
        )
        if db.get(Entity, eid) is None
    ]

    unassigned_demo: list[dict[str, str]] = []
    for name, expected_owner in DEMO_OWNERSHIP_BY_NAME.items():
        entity = db.query(Entity).filter(Entity.name == name).first()
        if entity is None:
            continue
        if not entity.owner_id:
            unassigned_demo.append({"name": name, "entity_id": entity.id, "expected_owner": expected_owner})

    return {
        "entity_count": len(rows),
        "by_type": dict(sorted(by_type.items())),
        "ontology_type_count": len(ontology_types),
        "missing_types": missing_types,
        "capability_count": cap_count,
        "missing_capabilities": missing_capabilities,
        "missing_infrastructure_ids": missing_infrastructure,
        "unassigned_demo_entities": unassigned_demo,
        "complete": (
            not missing_types
            and registry_audit["registry_complete"]
            and not missing_infrastructure
        ),
    }


def _ensure_infrastructure_entities(db: Session, *, org: Entity, rain: Entity, bob: Entity | None) -> list[str]:
    created: list[str] = []
    node_id = os.getenv("POCP_NODE_ID", "pocp-node-local")
    backend = os.getenv("BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")
    maintainer_id = org.id

    if db.get(Entity, LOCAL_COMPUTE_NODE_ID) is None:
        register_compute_node(
            db,
            entity_id=LOCAL_COMPUTE_NODE_ID,
            name="Local Compute Node",
            description="Platform-local GPU/CPU inference and witness compute",
            maintainer_id=maintainer_id,
            region="local",
            hardware={"gpu": "optional", "cpu": "available"},
            capabilities=["gpu_inference", "witness", "embeddings"],
            verification_methods=["log", "peer_witness"],
        )
        entity = db.get(Entity, LOCAL_COMPUTE_NODE_ID)
        if entity:
            meta = dict(entity.metadata_ or {})
            meta["node_id"] = node_id
            meta["endpoints"] = {"base_url": backend, "status": "/api/v1/intelligence/compute/status"}
            entity.metadata_ = meta
        created.append(LOCAL_COMPUTE_NODE_ID)

    if db.get(Entity, LOCAL_VERIFIER_NODE_ID) is None:
        register_verifier_node(
            db,
            entity_id=LOCAL_VERIFIER_NODE_ID,
            name="Local Verifier Node",
            description="Hybrid AI + peer witness verification for local federation",
            maintainer_id=maintainer_id,
            verifier_kinds=["ai_review", "peer_witness", "log"],
            service_endpoints={"witness": f"{backend}/api/v1/intelligence/compute/witness"},
            trust_level="standard",
        )
        created.append(LOCAL_VERIFIER_NODE_ID)

    if db.get(Entity, BOB_REVIEWER_NODE_ID) is None and bob is not None:
        register_reviewer_node(
            db,
            entity_id=BOB_REVIEWER_NODE_ID,
            name="Bob Review Queue",
            description="Human governance proxy review endpoint (Bob)",
            maintainer_id=bob.id,
            review_policy="governance_proxy",
            queue_capacity=50,
            supported_task_types=["contribution_review", "entity_governance"],
        )
        created.append(BOB_REVIEWER_NODE_ID)

    if db.get(Entity, RAIN_SPONSOR_ID) is None:
        register_sponsor_entity(
            db,
            entity_id=RAIN_SPONSOR_ID,
            name="Rain Sponsor Pool",
            description="Primary sponsor pool — Rain / PoCP AI Commons task bounties",
            maintainer_id=rain.id,
            sponsor_policy="task_bounty",
            accepted_units=["AIC", "CP"],
        )
        created.append(RAIN_SPONSOR_ID)

    if db.get(Entity, PROTOCOL_TREASURY_ID) is None:
        register_protocol_treasury(
            db,
            entity_id=PROTOCOL_TREASURY_ID,
            governance_entity_id=org.id,
            fee_schedule={"platform_fee_bps": 250, "settlement_unit": "AIC"},
        )
        created.append(PROTOCOL_TREASURY_ID)

    if db.get(Entity, STUDY_WORKFLOW_ID) is None:
        register_workflow(
            db,
            entity_id=STUDY_WORKFLOW_ID,
            name="Study Notes Workflow",
            description="Demo workflow — Rain authors, StudyAgent executes, R-Tutor skill assists",
            maintainer_id=maintainer_id,
            steps=[
                {"order": 1, "entity_type": "human", "role": "creator"},
                {"order": 2, "entity_type": "agent", "role": "executor"},
                {"order": 3, "entity_type": "skill", "role": "skill_provider"},
                {"order": 4, "entity_type": "tool", "role": "tool_provider"},
                {"order": 5, "entity_type": "llm", "role": "witness"},
            ],
            version="1.0.0",
            entrypoint="study_notes_demo",
        )
        created.append(STUDY_WORKFLOW_ID)

    return created


def _assign_demo_ownership(db: Session, *, rain: Entity) -> list[str]:
    assigned: list[str] = []
    for name, expected_owner in DEMO_OWNERSHIP_BY_NAME.items():
        entity = db.query(Entity).filter(Entity.name == name).first()
        if entity is None:
            continue
        owner_id = expected_owner if expected_owner != RAIN_ID else rain.id
        if not entity.owner_id:
            entity.owner_id = owner_id
            assigned.append(entity.id)
        if not entity.creator_id:
            entity.creator_id = owner_id
            if entity.id not in assigned:
                assigned.append(entity.id)
    return assigned


def _link_catalog_metadata(db: Session, *, org: Entity, rain: Entity) -> None:
    """Cross-link stable catalog IDs in entity metadata for discovery."""
    links = {
        RAIN_ID: {
            "sponsor_entity_id": RAIN_SPONSOR_ID,
            "reviewer_node_id": BOB_REVIEWER_NODE_ID,
        },
        org.id: {
            "compute_node_id": LOCAL_COMPUTE_NODE_ID,
            "verifier_node_id": LOCAL_VERIFIER_NODE_ID,
            "protocol_treasury_id": PROTOCOL_TREASURY_ID,
            "primary_sponsor_entity_id": RAIN_SPONSOR_ID,
        },
    }
    for entity_id, patch in links.items():
        entity = db.get(Entity, entity_id)
        if entity is None:
            continue
        meta = dict(entity.metadata_ or {})
        changed = False
        for key, value in patch.items():
            if meta.get(key) != value and db.get(Entity, value) is not None:
                meta[key] = value
                changed = True
        if changed:
            entity.metadata_ = meta


def _ensure_node_profiles(db: Session, *, backend_url: str) -> list[str]:
    """Register NodeProfile rows for infrastructure entities (idempotent)."""
    created: list[str] = []
    specs: list[tuple[str, str, str | None]] = [
        (LOCAL_COMPUTE_NODE_ID, "compute", backend_url),
        (LOCAL_VERIFIER_NODE_ID, "verifier", backend_url),
        (BOB_REVIEWER_NODE_ID, "reviewer", None),
        (RAIN_SPONSOR_ID, "service", None),
        (PROTOCOL_TREASURY_ID, "treasury", None),
    ]
    for entity_id, node_type, base_url in specs:
        if db.get(Entity, entity_id) is None:
            continue
        if get_node_by_entity(db, entity_id) is not None:
            continue
        record = register_node(
            db,
            entity_id=entity_id,
            node_type=node_type,
            base_url=base_url,
        )
        created.append(record.id)
    return created


def ensure_platform_entity_catalog(db: Session) -> dict[str, Any]:
    """Idempotently register infrastructure entities, capabilities, and demo ownership."""
    rain = db.get(Entity, RAIN_ID)
    org = _resolve_org(db)
    bob = _resolve_bob(db)
    if rain is None or org is None:
        return {"skipped": True, "reason": "rain or org missing"}

    infrastructure = _ensure_infrastructure_entities(db, org=org, rain=rain, bob=bob)
    ownership = _assign_demo_ownership(db, rain=rain)
    capabilities = seed_platform_capabilities(
        db, rain_id=rain.id, maintainer_id=org.id
    )
    backend = os.getenv("BACKEND_URL", "http://127.0.0.1:8008").rstrip("/")
    node_profiles = _ensure_node_profiles(db, backend_url=backend)
    _link_catalog_metadata(db, org=org, rain=rain)

    return {
        "skipped": False,
        "infrastructure_created": infrastructure,
        "ownership_assigned": ownership,
        "capabilities_created": capabilities,
        "node_profiles_created": node_profiles,
        "audit": audit_entity_catalog(db),
    }
