"""Agent Studio memory vault — DB + on-disk markdown repository per Meta Agent."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from meta_agents_spec import META_AGENT_BY_ID, META_AGENT_IDS, NEXUS_ID
from models.agent_studio import (
    AgentStudioMemory,
    StudioMemoryKind,
    StudioMemoryScope,
)

_REPO = Path(__file__).resolve().parents[3]
_MEMORY_ROOT = _REPO / "data" / "agent_studio" / "memory"
_STUDIO_SLUG = "_studio"


def memory_root() -> Path:
    return _MEMORY_ROOT


def agent_memory_dir(agent_entity_id: str) -> Path:
    if agent_entity_id == NEXUS_ID:
        slug = _STUDIO_SLUG
    else:
        slug = META_AGENT_BY_ID.get(agent_entity_id, {}).get("slug") or agent_entity_id
    return _MEMORY_ROOT / slug.replace("/", "_")


def default_memory_store_config(spec_slug: str) -> dict[str, Any]:
    rel = f"data/agent_studio/memory/{spec_slug if spec_slug != 'nexus-0' else _STUDIO_SLUG}"
    return {"path": rel, "max_entries": 500, "sync_files": True}


def memory_to_dict(m: AgentStudioMemory) -> dict[str, Any]:
    return {
        "id": m.id,
        "scope": m.scope.value,
        "agent_entity_id": m.agent_entity_id,
        "kind": m.kind.value,
        "title": m.title,
        "content": m.content,
        "source_type": m.source_type,
        "source_id": m.source_id,
        "tags": m.tags or [],
        "importance": m.importance,
        "metadata": m.metadata_ or {},
        "created_at": m.created_at.isoformat() if m.created_at else None,
        "file_path": (m.metadata_ or {}).get("file_path"),
    }


def append_memory(
    db: Session,
    *,
    agent_entity_id: str,
    title: str,
    content: str | None = None,
    kind: str = "episodic",
    scope: str = "agent",
    source_type: str | None = None,
    source_id: str | None = None,
    tags: list[str] | None = None,
    importance: float = 0.5,
    metadata: dict | None = None,
    sync_file: bool = True,
) -> AgentStudioMemory:
    if agent_entity_id not in META_AGENT_IDS:
        raise ValueError(f"Unknown Meta Agent: {agent_entity_id}")
    mem_scope = StudioMemoryScope.studio if scope == "studio" else StudioMemoryScope.agent
    owner = NEXUS_ID if mem_scope == StudioMemoryScope.studio else agent_entity_id

    entry = AgentStudioMemory(
        scope=mem_scope,
        agent_entity_id=owner,
        kind=StudioMemoryKind(kind),
        title=title[:512],
        content=content,
        source_type=source_type,
        source_id=source_id,
        tags=tags or [],
        importance=max(0.0, min(1.0, importance)),
        metadata_=metadata or {},
    )
    db.add(entry)
    db.flush()

    if sync_file:
        path = _write_memory_file(entry, subject_agent_id=agent_entity_id)
        meta = dict(entry.metadata_ or {})
        meta["file_path"] = str(path.relative_to(_REPO)).replace("\\", "/")
        entry.metadata_ = meta
        db.flush()

    return entry


def list_memories(
    db: Session,
    *,
    agent_entity_id: str | None = None,
    scope: str | None = None,
    kind: str | None = None,
    limit: int = 40,
    min_importance: float = 0.0,
) -> list[AgentStudioMemory]:
    q = db.query(AgentStudioMemory).order_by(
        AgentStudioMemory.importance.desc(),
        AgentStudioMemory.created_at.desc(),
    )
    if agent_entity_id:
        q = q.filter(AgentStudioMemory.agent_entity_id == agent_entity_id)
    if scope:
        q = q.filter(AgentStudioMemory.scope == StudioMemoryScope(scope))
    if kind:
        q = q.filter(AgentStudioMemory.kind == StudioMemoryKind(kind))
    if min_importance > 0:
        q = q.filter(AgentStudioMemory.importance >= min_importance)
    return q.limit(limit).all()


def memory_count(db: Session, agent_entity_id: str) -> int:
    return (
        db.query(func.count(AgentStudioMemory.id))
        .filter(AgentStudioMemory.agent_entity_id == agent_entity_id)
        .scalar()
        or 0
    )


def format_memory_context(
    db: Session,
    agent_entity_id: str,
    *,
    limit: int = 6,
) -> str:
    """Compact context block for Cursor handoff prompts."""
    rows = list_memories(db, agent_entity_id=agent_entity_id, limit=limit)
    if not rows:
        studio_rows = list_memories(
            db, agent_entity_id=NEXUS_ID, scope="studio", limit=3
        )
        rows = studio_rows
    if not rows:
        return "(no prior memories — first execution for this agent)"
    lines = []
    for m in rows:
        body = (m.content or "")[:400].replace("\n", " ")
        lines.append(f"- [{m.kind.value}] {m.title}: {body}")
    return "\n".join(lines)


def vault_summary(db: Session) -> dict[str, Any]:
    """Studio-wide memory vault stats."""
    per_agent: list[dict[str, Any]] = []
    total = 0
    for eid in sorted(META_AGENT_IDS):
        owner = NEXUS_ID if eid == NEXUS_ID else eid
        count = (
            db.query(func.count(AgentStudioMemory.id))
            .filter(AgentStudioMemory.agent_entity_id == owner)
            .scalar()
            or 0
        )
        if eid != NEXUS_ID:
            agent_count = (
                db.query(func.count(AgentStudioMemory.id))
                .filter(
                    AgentStudioMemory.agent_entity_id == eid,
                    AgentStudioMemory.scope == StudioMemoryScope.agent,
                )
                .scalar()
                or 0
            )
            count = agent_count
        total += count
        spec = META_AGENT_BY_ID.get(eid, {})
        per_agent.append(
            {
                "entity_id": eid,
                "name": spec.get("name"),
                "slug": spec.get("slug"),
                "memory_count": count,
                "memory_dir": str(agent_memory_dir(eid).relative_to(_REPO)).replace("\\", "/"),
            }
        )
    studio_count = (
        db.query(func.count(AgentStudioMemory.id))
        .filter(
            AgentStudioMemory.scope == StudioMemoryScope.studio,
            AgentStudioMemory.agent_entity_id == NEXUS_ID,
        )
        .scalar()
        or 0
    )
    return {
        "vault_root": str(_MEMORY_ROOT.relative_to(_REPO)).replace("\\", "/"),
        "total_entries": total,
        "studio_collective_entries": studio_count,
        "agents": per_agent,
    }


def _write_memory_file(entry: AgentStudioMemory, *, subject_agent_id: str) -> Path:
    directory = agent_memory_dir(subject_agent_id)
    directory.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^\w\-]+", "_", entry.title)[:60].strip("_") or "memory"
    ts = entry.created_at.strftime("%Y%m%dT%H%M%S") if entry.created_at else datetime.utcnow().strftime(
        "%Y%m%dT%H%M%S"
    )
    path = directory / f"{ts}_{safe[:40]}.md"
    spec = META_AGENT_BY_ID.get(subject_agent_id, {})
    lines = [
        f"# {entry.title}",
        "",
        f"- **Agent:** {spec.get('name', subject_agent_id)}",
        f"- **Kind:** {entry.kind.value}",
        f"- **Scope:** {entry.scope.value}",
        f"- **Source:** {entry.source_type or 'manual'} `{entry.source_id or ''}`",
        f"- **Tags:** {', '.join(entry.tags or [])}",
        f"- **Importance:** {entry.importance}",
        "",
        entry.content or "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
