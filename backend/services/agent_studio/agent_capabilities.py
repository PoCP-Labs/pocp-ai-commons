"""Meta Agent capability registry — baseline spec + evolved capabilities."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from meta_agents_spec import META_AGENT_BY_ID, META_AGENT_IDS
from models.agent import Agent
from services.agent_studio.memory_store import memory_count


def get_agent_capabilities(db: Session, agent_entity_id: str) -> dict[str, Any]:
    if agent_entity_id not in META_AGENT_IDS:
        raise ValueError("Not a Meta Agent")
    spec = META_AGENT_BY_ID.get(agent_entity_id, {})
    agent = db.query(Agent).filter(Agent.entity_id == agent_entity_id).first()
    config = dict(agent.config or {}) if agent else {}
    profile = dict(config.get("learning_profile") or {})
    baseline = list(spec.get("capabilities") or [])
    evolved = list(profile.get("evolved_capabilities") or [])
    strengths = list(profile.get("strengths") or [])
    merged = _unique_caps(baseline + evolved + strengths)
    return {
        "agent_entity_id": agent_entity_id,
        "name": spec.get("name"),
        "slug": spec.get("slug"),
        "baseline_capabilities": baseline,
        "evolved_capabilities": evolved,
        "effective_capabilities": merged,
        "roles": spec.get("roles") or [],
        "evolution_version": profile.get("evolution_version", 0),
        "memory_count": memory_count(db, agent_entity_id),
    }


def evolve_capability(
    db: Session,
    agent_entity_id: str,
    capability: str,
    *,
    source: str = "auto_evolution",
    evidence: dict | None = None,
) -> dict[str, Any]:
    """Append an evolved capability and record a capability memory."""
    if agent_entity_id not in META_AGENT_IDS:
        raise ValueError("Not a Meta Agent")
    agent = db.query(Agent).filter(Agent.entity_id == agent_entity_id).first()
    if agent is None:
        raise ValueError("Agent row missing")

    config = dict(agent.config or {})
    profile = dict(config.get("learning_profile") or {})
    evolved = list(profile.get("evolved_capabilities") or [])
    cap = capability.strip()
    if cap and cap not in evolved:
        evolved.append(cap)
    profile["evolved_capabilities"] = evolved[-25:]
    profile["evolution_version"] = int(profile.get("evolution_version", 0)) + 1
    profile["last_capability_evolution"] = {
        "capability": cap,
        "source": source,
        "at": __import__("datetime").datetime.utcnow().isoformat() + "Z",
    }
    config["learning_profile"] = profile
    agent.config = config
    db.flush()

    from services.agent_studio.memory_store import append_memory

    append_memory(
        db,
        agent_entity_id=agent_entity_id,
        title=f"Capability evolved: {cap}",
        content=f"Source: {source}. Evidence: {evidence or {}}",
        kind="capability",
        source_type=source,
        tags=["capability", "evolution"],
        importance=0.7,
        sync_file=False,
    )
    return get_agent_capabilities(db, agent_entity_id)


def _unique_caps(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        key = (item or "").strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(item.strip())
    return out


def studio_capability_matrix(db: Session) -> list[dict[str, Any]]:
    return [get_agent_capabilities(db, eid) for eid in sorted(META_AGENT_IDS)]
