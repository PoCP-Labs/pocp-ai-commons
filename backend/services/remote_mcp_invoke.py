"""Execute MCP invoke on behalf of a trusted peer node (federated MCP routing)."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from models.entity import Entity, EntityType
from services.mcp_client import McpClientError, call_mcp_tool as wire_call_mcp_tool
from services.mcp_import import MCP_SOURCE


def find_mcp_tool_by_portable_id(db: Session, portable_id: str) -> tuple[Entity, dict[str, Any]] | None:
    for entity in db.query(Entity).filter(Entity.entity_type == EntityType.tool).all():
        meta = entity.metadata_ or {}
        if meta.get("capability_source") != MCP_SOURCE or meta.get("mcp_role") != "tool":
            continue
        if meta.get("portable_id") == portable_id:
            return entity, meta
    return None


def _resolve_server_entity(db: Session, meta: dict[str, Any]) -> Entity | None:
    server_id = meta.get("mcp_server_entity_id")
    if server_id:
        server = db.get(Entity, server_id)
        if server and server.entity_type == EntityType.tool:
            return server
    return None


async def run_remote_mcp_invoke(
    db: Session,
    *,
    portable_id: str,
    arguments: dict[str, Any] | None = None,
    invoke_mode: str | None = "live",
) -> dict[str, Any]:
    """Peer-facing MCP invoke by portable_id — no human initiator on this node."""
    found = find_mcp_tool_by_portable_id(db, portable_id)
    if not found:
        raise HTTPException(status_code=404, detail=f"MCP tool not found for portable_id: {portable_id}")

    tool_entity, meta = found
    server_entity = _resolve_server_entity(db, meta)
    args = arguments or {}
    mode = (invoke_mode or "live").lower()
    tool_name = str(meta.get("mcp_tool_name") or tool_entity.name)

    if mode == "stub":
        return {
            "portable_id": portable_id,
            "invoke_mode": "stub",
            "mcp_tool_name": meta.get("mcp_tool_name"),
            "output": {
                "content": [
                    {
                        "type": "text",
                        "text": f"[Peer MCP stub] {tool_name} portable_id={portable_id} args={args!r}",
                    }
                ],
                "isError": False,
            },
        }

    if not server_entity:
        raise HTTPException(status_code=400, detail="MCP server entity missing for portable tool")
    server_transport = (server_entity.metadata_ or {}).get("mcp_transport")
    if not server_transport:
        raise HTTPException(status_code=400, detail="MCP server transport not configured")

    try:
        output = await wire_call_mcp_tool(server_transport, tool_name=tool_name, arguments=args)
    except McpClientError as exc:
        raise HTTPException(status_code=502, detail=f"Peer MCP live invoke failed: {exc}") from exc

    return {
        "portable_id": portable_id,
        "invoke_mode": "live",
        "mcp_tool_name": meta.get("mcp_tool_name"),
        "mcp_server_id": meta.get("mcp_server_id"),
        "output": output,
    }
