"""Import Model Context Protocol (MCP) servers and tools as PoCP Tool entities."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from models.entity import Entity, EntityStatus, EntityType
from services.capability_import import (
    _resolve_import_status,
    activate_capability,
    capability_source_key,
    load_capability_sources,
)

MCP_SOURCE = "mcp"
MCP_SPEC_VERSION = "2024-11-05"
BUNDLED_MCP_DIR = Path(__file__).resolve().parents[1] / "config" / "capabilities" / "bundled" / "mcp"


def _find_tool_by_source_key(db: Session, source_key: str) -> Entity | None:
    for entity in db.query(Entity).filter(Entity.entity_type == EntityType.tool).all():
        meta = entity.metadata_ or {}
        if meta.get("capability_source_key") == source_key:
            return entity
    return None


def normalize_mcp_transport(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalize stdio vs HTTP/SSE transport fields."""
    if raw.get("url"):
        return {
            "transport": "http",
            "url": str(raw["url"]).strip(),
            "headers": dict(raw.get("headers") or {}),
        }
    command = raw.get("command")
    if not command:
        raise ValueError("MCP server requires 'command' (stdio) or 'url' (http/sse)")
    args = raw.get("args") or []
    if not isinstance(args, list):
        raise ValueError("MCP 'args' must be a list of strings")
    return {
        "transport": "stdio",
        "command": str(command),
        "args": [str(a) for a in args],
        "env": dict(raw.get("env") or {}),
    }


def parse_mcp_servers_config(config: dict[str, Any]) -> list[dict[str, Any]]:
    """Parse Cursor/Claude-style { \"mcpServers\": { name: { command, args } } }."""
    servers = config.get("mcpServers") or config.get("servers") or {}
    if not isinstance(servers, dict):
        raise ValueError("mcpServers must be an object")
    rows: list[dict[str, Any]] = []
    for slug, spec in servers.items():
        if not isinstance(spec, dict):
            continue
        tools = spec.get("tools") if isinstance(spec.get("tools"), list) else []
        transport_fields = {
            k: v for k, v in spec.items() if k not in ("tools", "name", "description")
        }
        transport = normalize_mcp_transport(transport_fields)
        rows.append(
            {
                "external_id": slug,
                "name": spec.get("name") or slug.replace("-", " ").replace("_", " ").title(),
                "description": spec.get("description"),
                "transport": transport,
                "tools": tools or [],
            }
        )
    return rows


def import_mcp_server(
    db: Session,
    *,
    external_id: str,
    name: str,
    description: str | None,
    maintainer_id: str,
    transport: dict[str, Any],
    tools: list[dict[str, Any]] | None = None,
    activate: bool | None = None,
    import_tools: bool = True,
) -> dict[str, Any]:
    """Register an MCP server as a Tool entity; optionally register each MCP tool."""
    source_key = capability_source_key(MCP_SOURCE, external_id)
    status = _resolve_import_status(MCP_SOURCE, activate=activate)
    transport_norm = normalize_mcp_transport(transport) if "transport" not in transport else transport

    entity = _find_tool_by_source_key(db, source_key)
    metadata = {
        "capability_source": MCP_SOURCE,
        "capability_source_key": source_key,
        "capability_external_id": external_id,
        "mcp_role": "server",
        "mcp_transport": transport_norm,
        "registry_compat": "mcp-import-v0.1",
        "mcp_spec_version": MCP_SPEC_VERSION,
        "imported_via": "mcp_import",
        "portable_id": f"mcp:{external_id}",
    }

    if entity is None:
        entity = Entity(
            entity_type=EntityType.tool,
            name=name,
            description=description or f"MCP server: {external_id}",
            owner_id=maintainer_id,
            creator_id=maintainer_id,
            status=status,
            metadata_=metadata,
        )
        db.add(entity)
        created = True
    else:
        entity.name = name
        entity.description = description or entity.description
        entity.status = status
        entity.metadata_ = {**(entity.metadata_ or {}), **metadata}
        created = False

    db.flush()
    tool_results: list[dict[str, Any]] = []
    if import_tools and tools:
        for tool_spec in tools:
            tool_results.append(
                import_mcp_tool(
                    db,
                    server_external_id=external_id,
                    server_entity_id=entity.id,
                    maintainer_id=maintainer_id,
                    tool_name=str(tool_spec.get("name") or tool_spec.get("tool") or ""),
                    description=tool_spec.get("description"),
                    input_schema=tool_spec.get("inputSchema") or tool_spec.get("input_schema"),
                    activate=activate,
                )
            )

    return {
        "created": created,
        "entity_id": entity.id,
        "entity_type": entity.entity_type.value,
        "name": entity.name,
        "status": entity.status.value,
        "capability_source_key": source_key,
        "mcp_role": "server",
        "tools_imported": len(tool_results),
        "tools": tool_results,
    }


def import_mcp_tool(
    db: Session,
    *,
    server_external_id: str,
    server_entity_id: str,
    maintainer_id: str,
    tool_name: str,
    description: str | None = None,
    input_schema: dict | None = None,
    activate: bool | None = None,
) -> dict[str, Any]:
    if not tool_name.strip():
        raise ValueError("MCP tool name is required")

    ext_id = f"{server_external_id}/{tool_name}"
    source_key = capability_source_key(MCP_SOURCE, ext_id)
    status = _resolve_import_status(MCP_SOURCE, activate=activate)

    entity = _find_tool_by_source_key(db, source_key)
    metadata = {
        "capability_source": MCP_SOURCE,
        "capability_source_key": source_key,
        "capability_external_id": ext_id,
        "mcp_role": "tool",
        "mcp_server_id": server_external_id,
        "mcp_server_entity_id": server_entity_id,
        "mcp_tool_name": tool_name,
        "input_schema": input_schema or {},
        "registry_compat": "mcp-import-v0.1",
        "mcp_spec_version": MCP_SPEC_VERSION,
        "imported_via": "mcp_import",
        "portable_id": f"mcp:{ext_id}",
    }

    display = tool_name.replace("_", " ").title()
    if entity is None:
        entity = Entity(
            entity_type=EntityType.tool,
            name=f"{display} (MCP)",
            description=description or f"MCP tool `{tool_name}` on server `{server_external_id}`",
            owner_id=maintainer_id,
            creator_id=maintainer_id,
            status=status,
            metadata_=metadata,
        )
        db.add(entity)
        created = True
    else:
        entity.name = f"{display} (MCP)"
        entity.description = description or entity.description
        entity.status = status
        entity.metadata_ = {**(entity.metadata_ or {}), **metadata}
        created = False

    db.flush()
    return {
        "created": created,
        "entity_id": entity.id,
        "entity_type": entity.entity_type.value,
        "name": entity.name,
        "status": entity.status.value,
        "capability_source_key": source_key,
        "mcp_role": "tool",
        "mcp_tool_name": tool_name,
    }


def import_mcp_from_manifest_file(
    db: Session,
    path: Path,
    *,
    maintainer_id: str,
    activate: bool | None = None,
) -> list[dict[str, Any]]:
    """Load a bundled JSON manifest (single server or mcpServers map)."""
    data = json.loads(path.read_text(encoding="utf-8"))
    results: list[dict[str, Any]] = []

    if "mcpServers" in data or "servers" in data:
        for row in parse_mcp_servers_config(data):
            results.append(
                import_mcp_server(
                    db,
                    external_id=row["external_id"],
                    name=row["name"],
                    description=row.get("description"),
                    maintainer_id=maintainer_id,
                    transport=row["transport"],
                    tools=row.get("tools") or [],
                    activate=activate,
                )
            )
        return results

    external_id = str(data.get("external_id") or path.stem)
    transport = data.get("transport") or {
        k: data[k] for k in ("command", "args", "env", "url", "headers") if k in data
    }
    results.append(
        import_mcp_server(
            db,
            external_id=external_id,
            name=str(data.get("name") or external_id),
            description=data.get("description"),
            maintainer_id=maintainer_id,
            transport=transport,
            tools=data.get("tools") or [],
            activate=activate,
        )
    )
    return results


def sync_bundled_mcp_capabilities(
    db: Session,
    *,
    maintainer_id: str | None = None,
    activate: bool | None = False,
) -> list[dict[str, Any]]:
    """Import example MCP manifests from config/capabilities/bundled/mcp/."""
    if not BUNDLED_MCP_DIR.is_dir():
        return []

    org = db.query(Entity).filter(Entity.name == "PoCP AI Commons").first()
    owner = maintainer_id or (org.id if org else None)
    if not owner:
        return []

    results: list[dict[str, Any]] = []
    for manifest in sorted(BUNDLED_MCP_DIR.glob("*.json")):
        for item in import_mcp_from_manifest_file(
            db, manifest, maintainer_id=owner, activate=activate
        ):
            results.append({**item, "manifest": manifest.name})
    return results


def list_mcp_catalog(db: Session) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for entity in db.query(Entity).filter(Entity.entity_type == EntityType.tool).all():
        meta = entity.metadata_ or {}
        if meta.get("capability_source") != MCP_SOURCE:
            continue
        rows.append(
            {
                "entity_id": entity.id,
                "name": entity.name,
                "status": entity.status.value,
                "mcp_role": meta.get("mcp_role"),
                "mcp_tool_name": meta.get("mcp_tool_name"),
                "mcp_server_id": meta.get("mcp_server_id"),
                "mcp_transport": meta.get("mcp_transport"),
                "portable_id": meta.get("portable_id"),
            }
        )
    return rows
