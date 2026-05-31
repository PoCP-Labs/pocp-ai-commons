"""A2A Agent Card builder — BI-1 discovery adapter for PoCP Entity intelligence."""

from __future__ import annotations

import os
from typing import Any

from sqlalchemy.orm import Session

from intelligence.protocol import CAPABILITY_LAYER_VERSION, PROTOCOL_VERSION
from models.entity import Entity, EntityType
from services.compute_profile import get_compute_profile

POCP_A2A_EXTENSION_URI = "urn:pocp:extension:contribution-protocol:0.1"
POCP_A2A_CARD_VERSION = "0.1.0"
A2A_PROTOCOL_VERSION = "0.2.0"

_DEFAULT_INPUT = ["text/plain", "application/json"]
_DEFAULT_OUTPUT = ["text/plain", "application/json"]


def public_backend_url() -> str:
    return (
        os.getenv("POCP_PUBLIC_URL")
        or os.getenv("BACKEND_URL")
        or "http://127.0.0.1:8000"
    ).rstrip("/")


def _pocp_extension(*, entity_id: str | None = None) -> dict[str, Any]:
    base = public_backend_url()
    ext: dict[str, Any] = {
        "uri": POCP_A2A_EXTENSION_URI,
        "description": (
            "PoCP contribution protocol — tasks bind to Contribution events; "
            "witness quorum + policy auto-finalization; ledger remembers."
        ),
        "required": True,
    }
    params: dict[str, Any] = {
        "protocol_version": PROTOCOL_VERSION,
        "capability_layer_version": CAPABILITY_LAYER_VERSION,
        "contribution_api": f"{base}/api/v1/contributions",
        "intelligence_api": f"{base}/api/v1/intelligence",
    }
    if entity_id:
        params["entity_id"] = entity_id
        params["profile_api"] = f"{base}/api/v1/intelligence/entities/{entity_id}/profile"
    ext["params"] = params
    return ext


def _security_block() -> dict[str, Any]:
    return {
        "securitySchemes": {
            "bearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "description": "PoCP access token from /api/v1/auth/dev-login or GitHub OAuth",
            }
        },
        "security": [{"bearerAuth": []}],
    }


def _base_capabilities(*, streaming: bool = False) -> dict[str, Any]:
    return {
        "streaming": streaming,
        "pushNotifications": False,
        "stateTransitionHistory": True,
        "extensions": [_pocp_extension()],
    }


def _skill(
    *,
    skill_id: str,
    name: str,
    description: str,
    tags: list[str],
    examples: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "id": skill_id,
        "name": name,
        "description": description,
        "tags": tags,
        "examples": examples or [],
        "inputModes": list(_DEFAULT_INPUT),
        "outputModes": list(_DEFAULT_OUTPUT),
    }


def _skills_from_compute_profile(profile: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not profile:
        return []
    skills: list[dict[str, Any]] = []
    for offer in profile.get("offers") or []:
        if not isinstance(offer, dict):
            continue
        cap = str(offer.get("capability") or "").strip()
        if not cap:
            continue
        adapters = offer.get("adapters") or []
        adapter_text = ", ".join(str(a) for a in adapters) if adapters else "default"
        models = offer.get("models") or []
        model_text = ", ".join(str(m) for m in models[:3]) if models else ""
        desc = f"ComputeProfile offer: {cap} via {adapter_text}"
        if model_text:
            desc = f"{desc} ({model_text})"
        skills.append(
            _skill(
                skill_id=f"compute-{cap}",
                name=cap.replace("_", " ").title(),
                description=desc,
                tags=["compute", cap, "distributed-compute"],
            )
        )
    return skills


def _skills_from_entity(entity: Entity) -> list[dict[str, Any]]:
    meta = entity.metadata_ or {}
    declared = meta.get("capabilities") or []
    tags = meta.get("tags") or []
    et = entity.entity_type.value

    skills: list[dict[str, Any]] = []

    type_defaults: dict[str, list[dict[str, Any]]] = {
        "human": [
            _skill(
                skill_id="contribution-submit",
                name="Submit Contribution",
                description="Create contribution events with evidence for network verification",
                tags=["contribution", "human", *tags[:3]],
                examples=["Submit a knowledge contribution with evidence"],
            ),
        ],
        "agent": [
            _skill(
                skill_id="study-agent-run",
                name="Study Agent Run",
                description="Multi-step research agent with InvocationTrace binding",
                tags=["agent", "orchestration", *tags[:3]],
                examples=["Run StudyAgent on a research topic"],
            ),
            _skill(
                skill_id="capability-match",
                name="Capability Match",
                description="Recommend agents and skills for tasks",
                tags=["matching", "agent", *tags[:3]],
            ),
        ],
        "skill": [
            _skill(
                skill_id="skill-execute",
                name="Skill Execute",
                description="Invoke skill capability chain (LLM / tool steps)",
                tags=["skill", "execute", *tags[:3]],
            ),
        ],
        "llm": [
            _skill(
                skill_id="witness-verify",
                name="Witness Verification",
                description="Advisory multi-dimensional contribution verification",
                tags=["witness", "llm", "verification", *tags[:3]],
            ),
        ],
        "tool": [
            _skill(
                skill_id="mcp-invoke",
                name="MCP Tool Invoke",
                description="Remote MCP tool execution with trace metadata",
                tags=["tool", "mcp", *tags[:3]],
            ),
        ],
        "dataset": [
            _skill(
                skill_id="evidence-bind",
                name="Evidence Binding",
                description="Bind dataset references into contribution evidence",
                tags=["dataset", "evidence", *tags[:3]],
            ),
        ],
        "workflow": [
            _skill(
                skill_id="topology-coordinate",
                name="Workflow Coordinate",
                description="Coordinate multi-entity contribution topology",
                tags=["workflow", "coordinate", *tags[:3]],
            ),
        ],
        "organization": [
            _skill(
                skill_id="governance-summary",
                name="Governance Summary",
                description="Organization-level governance advisory summaries",
                tags=["organization", "governance", *tags[:3]],
            ),
        ],
        "community": [
            _skill(
                skill_id="federation-intel",
                name="Federation Intelligence",
                description="Cross-node intelligence export and peer federation",
                tags=["community", "federation", *tags[:3]],
            ),
        ],
    }

    skills.extend(type_defaults.get(et, []))

    for idx, cap in enumerate(declared):
        cap_str = str(cap).strip()
        if not cap_str:
            continue
        skills.append(
            _skill(
                skill_id=f"declared-{cap_str.replace(' ', '-')[:40]}-{idx}",
                name=cap_str,
                description=f"Declared capability on Entity metadata",
                tags=["declared", cap_str, et, *tags[:2]],
            )
        )

    compute_profile = get_compute_profile(entity)
    skills.extend(_skills_from_compute_profile(compute_profile))

    # De-dupe by skill id
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for skill in skills:
        sid = skill["id"]
        if sid in seen:
            continue
        seen.add(sid)
        unique.append(skill)
    return unique or [
        _skill(
            skill_id="contribution-participate",
            name="Contribution Participate",
            description="Participate in PoCP contribution events",
            tags=["contribution", et],
        )
    ]


def _provider_block(db: Session, entity: Entity | None) -> dict[str, str] | None:
    if entity is None:
        return {
            "organization": "PoCP AI Commons",
            "url": public_backend_url(),
        }
    owner_id = entity.owner_id or entity.creator_id
    if owner_id:
        owner = db.get(Entity, owner_id)
        if owner and owner.entity_type == EntityType.organization:
            return {"organization": owner.name, "url": public_backend_url()}
        if owner:
            return {"organization": owner.name, "url": public_backend_url()}
    if entity.entity_type == EntityType.organization:
        return {"organization": entity.name, "url": public_backend_url()}
    return {"organization": "PoCP AI Commons", "url": public_backend_url()}


def build_entity_agent_card(db: Session, entity_id: str) -> dict[str, Any] | None:
    entity = db.get(Entity, entity_id)
    if entity is None:
        return None

    base = public_backend_url()
    description = entity.description or (
        f"PoCP {entity.entity_type.value} entity — participates through verified contributions."
    )
    if entity.status.value != "active":
        description = f"[{entity.status.value}] {description}"

    from services.finalization import is_auto_finalization_enabled

    auto_finalize = is_auto_finalization_enabled()
    card: dict[str, Any] = {
        "name": entity.name,
        "description": description,
        "url": f"{base}/api/v1/intelligence/entities/{entity.id}/a2a",
        "version": POCP_A2A_CARD_VERSION,
        "documentationUrl": f"{base}/api/v1/intelligence/entities/{entity.id}/profile",
        "capabilities": _base_capabilities(),
        "defaultInputModes": list(_DEFAULT_INPUT),
        "defaultOutputModes": list(_DEFAULT_OUTPUT),
        "skills": _skills_from_entity(entity),
        "provider": _provider_block(db, entity),
        "pocp": {
            "entity_id": entity.id,
            "entity_type": entity.entity_type.value,
            "status": entity.status.value,
            "owner_id": entity.owner_id,
            "protocol_version": PROTOCOL_VERSION,
            "a2a_protocol_version": A2A_PROTOCOL_VERSION,
            "advisory_only": True,
            "auto_finalization_enabled": auto_finalize,
            "finalization_mode": "entity_equal_policy_delegate",
        },
    }
    card.update(_security_block())
    card["capabilities"]["extensions"] = [_pocp_extension(entity_id=entity.id)]
    return card


def build_node_agent_card(db: Session) -> dict[str, Any]:
    """Node-level Agent Card for /.well-known/agent.json discovery."""
    base = public_backend_url()
    from services.compute_registry import compute_status_manifest
    from services.finalization import is_auto_finalization_enabled

    manifest = compute_status_manifest()
    node_id = manifest.get("node_id") or "local"
    auto_finalize = is_auto_finalization_enabled()

    skills = [
        _skill(
            skill_id="intelligence-match",
            name="Capability Match",
            description="Match tasks to agents, skills, and compute providers",
            tags=["matching", "intelligence"],
            examples=["Find skills for a documentation task"],
        ),
        _skill(
            skill_id="contribution-verify",
            name="Contribution Verify",
            description="Multi-witness advisory verification consensus",
            tags=["verification", "witness"],
        ),
        _skill(
            skill_id="study-agent",
            name="Study Agent",
            description="Run StudyAgent orchestration with optional contribution submit",
            tags=["agent", "study"],
        ),
        _skill(
            skill_id="compute-schedule",
            name="Compute Schedule",
            description="Schedule witness / llm_inference jobs on Entity providers or peers",
            tags=["compute", "scheduler"],
        ),
        _skill(
            skill_id="federation-intel-export",
            name="Federation Export",
            description="Export portable intelligence packets for trusted peers",
            tags=["federation", "export"],
        ),
    ]

    active_adapters = manifest.get("active_adapters") or []
    for adapter in active_adapters[:6]:
        skills.append(
            _skill(
                skill_id=f"node-adapter-{adapter}",
                name=f"Node Adapter: {adapter}",
                description=f"Local compute adapter active on node {node_id}",
                tags=["compute", "node", adapter],
            )
        )

    card: dict[str, Any] = {
        "name": os.getenv("POCP_NODE_NAME", "PoCP AI Commons Node"),
        "description": (
            "PoCP distributed intelligence node — witness quorum, matching, agents, "
            "graph analytics, and Entity-attached compute routing. "
            "AI witnesses; policy finalizes; ledger remembers."
        ),
        "url": f"{base}/api/v1/intelligence/a2a",
        "version": POCP_A2A_CARD_VERSION,
        "documentationUrl": f"{base}/api/v1/intelligence/protocol",
        "capabilities": _base_capabilities(streaming=False),
        "defaultInputModes": list(_DEFAULT_INPUT),
        "defaultOutputModes": list(_DEFAULT_OUTPUT),
        "skills": skills,
        "provider": _provider_block(db, None),
        "pocp": {
            "node_id": node_id,
            "protocol_version": PROTOCOL_VERSION,
            "capability_layer_version": CAPABILITY_LAYER_VERSION,
            "a2a_protocol_version": A2A_PROTOCOL_VERSION,
            "compute_manifest": {
                "active_adapters": active_adapters,
                "peer_compute_enabled": manifest.get("peer_compute_enabled"),
            },
            "advisory_only": True,
            "auto_finalization_enabled": auto_finalize,
            "finalization_mode": "entity_equal_policy_delegate",
        },
    }
    card.update(_security_block())
    card["capabilities"]["extensions"] = [_pocp_extension()]
    return card
