"""MCP tool invocation — stub, live wire protocol, or external result reporting."""

from __future__ import annotations

import json
import os
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from models.entity import Entity, EntityStatus, EntityType
from models.invocation import InvocationStatus, InvocationStep, InvocationTrace
from services.capability_receipt import build_capability_receipt
from services.mcp_client import McpClientError, call_mcp_tool as wire_call_mcp_tool
from services.mcp_import import MCP_SOURCE, MCP_SPEC_VERSION
from services.peer_mcp import MCP_PEER_PROVIDER, PeerMcpError, peer_mcp_enabled, peer_mcp_prefer_peer, try_peer_mcp_invoke

MCP_STUB_PROVIDER = "mcp-stub"
MCP_LIVE_PROVIDER = "mcp-live"
MCP_EXTERNAL_PROVIDER = "mcp-external"


def _live_invoke_enabled(meta: dict[str, Any], server_meta: dict[str, Any] | None) -> bool:
    env_on = os.getenv("ENABLE_MCP_LIVE_INVOKE", "").lower() in ("1", "true", "yes")
    runtime = meta.get("runtime") or {}
    server_runtime = (server_meta or {}).get("runtime") or {}
    if runtime.get("stub") or server_runtime.get("stub"):
        return False
    return env_on or bool(runtime.get("live") or server_runtime.get("live"))


def _require_human(db: Session, entity_id: str) -> Entity:
    entity = db.get(Entity, entity_id)
    if not entity or entity.entity_type != EntityType.human:
        raise HTTPException(status_code=400, detail="Initiator must be a human entity")
    return entity


def _require_mcp_tool(db: Session, tool_entity_id: str) -> tuple[Entity, dict[str, Any]]:
    entity = db.get(Entity, tool_entity_id)
    if not entity or entity.entity_type != EntityType.tool:
        raise HTTPException(status_code=404, detail="MCP tool entity not found")
    meta = entity.metadata_ or {}
    if meta.get("capability_source") != MCP_SOURCE or meta.get("mcp_role") != "tool":
        raise HTTPException(status_code=400, detail="Entity is not an imported MCP tool")
    if entity.status != EntityStatus.active:
        raise HTTPException(
            status_code=400,
            detail=f"MCP tool must be active before invoke (current: {entity.status.value})",
        )
    return entity, meta


def _resolve_server_entity(db: Session, meta: dict[str, Any]) -> Entity | None:
    server_id = meta.get("mcp_server_entity_id")
    if server_id:
        server = db.get(Entity, server_id)
        if server and server.entity_type == EntityType.tool:
            return server
    return None


def _normalize_external_result(raw: dict[str, Any]) -> dict[str, Any]:
    if "content" in raw:
        return raw
    if "output" in raw:
        text = raw["output"]
        return {"content": [{"type": "text", "text": str(text)}], "isError": bool(raw.get("isError"))}
    if "text" in raw:
        return {"content": [{"type": "text", "text": str(raw["text"])}], "isError": bool(raw.get("isError"))}
    return {"content": [{"type": "text", "text": str(raw)}], "isError": False}


def _output_text(output: dict[str, Any]) -> str:
    parts: list[str] = []
    for item in output.get("content") or []:
        if isinstance(item, dict) and item.get("type") == "text":
            parts.append(str(item.get("text") or ""))
    return "\n".join(parts).strip()


def _arguments_summary(arguments: dict[str, Any]) -> str:
    return json.dumps(arguments, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _record_mcp_trace(
    db: Session,
    *,
    human_id: str,
    tool_entity_id: str,
    server_entity_id: str | None,
    agent_entity_id: str | None,
    task_id: str | None,
    contribution_id: str | None,
    model_provider: str,
    status: InvocationStatus = InvocationStatus.completed,
    peer_node_id: str | None = None,
    step_metadata: list[dict | None] | None = None,
) -> InvocationTrace:
    chain: list[tuple[str, str, str]] = []
    if agent_entity_id:
        agent = db.get(Entity, agent_entity_id)
        if not agent or agent.entity_type != EntityType.agent:
            raise HTTPException(status_code=404, detail="Agent entity not found")
        chain.append((human_id, agent_entity_id, "uses"))
        chain.append((agent_entity_id, tool_entity_id, "calls"))
    else:
        chain.append((human_id, tool_entity_id, "uses"))
    if server_entity_id:
        chain.append((tool_entity_id, server_entity_id, "invokes_peer_mcp" if peer_node_id else "invokes_mcp"))
    else:
        chain.append((tool_entity_id, tool_entity_id, "invokes_peer_mcp" if peer_node_id else "invokes_mcp"))

    trace = InvocationTrace(
        initiator_id=human_id,
        task_id=task_id,
        contribution_id=contribution_id,
        model_provider=model_provider,
        status=status,
    )
    db.add(trace)
    db.flush()
    meta_list = step_metadata or [None] * len(chain)
    for order, (source_id, target_id, action) in enumerate(chain, start=1):
        step_meta = meta_list[order - 1] if order - 1 < len(meta_list) else None
        db.add(
            InvocationStep(
                trace_id=trace.id,
                step_order=order,
                source_entity_id=source_id,
                target_entity_id=target_id,
                action=action,
                metadata_=step_meta,
            )
        )
    db.flush()
    return trace


def _load_trace(db: Session, trace_id: str) -> InvocationTrace:
    trace = (
        db.query(InvocationTrace)
        .options(joinedload(InvocationTrace.steps))
        .filter(InvocationTrace.id == trace_id)
        .first()
    )
    if not trace:
        raise HTTPException(status_code=404, detail="Invocation trace not found")
    return trace


def _build_stub_output(
    *,
    tool_entity: Entity,
    meta: dict[str, Any],
    server_entity: Entity | None,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    runtime = meta.get("runtime") or {}
    if runtime.get("mock_output") is not None:
        mock = runtime["mock_output"]
        if isinstance(mock, dict):
            return mock
        return {"content": [{"type": "text", "text": str(mock)}], "isError": False}

    tool_name = meta.get("mcp_tool_name") or tool_entity.name
    server_id = meta.get("mcp_server_id") or (server_entity and server_entity.name)
    transport = (server_entity.metadata_ or {}).get("mcp_transport") if server_entity else None
    transport_kind = (transport or {}).get("transport", "unknown")

    summary = (
        f"[PoCP MCP stub] Would call `{tool_name}` on server `{server_id}` "
        f"via {transport_kind} transport with arguments: {arguments!r}. "
        "Set ENABLE_MCP_LIVE_INVOKE=true or runtime.live on the tool/server to wire-call MCP."
    )
    return {"content": [{"type": "text", "text": summary}], "isError": False}


async def _try_peer_output(
    *,
    meta: dict[str, Any],
    arguments: dict[str, Any],
    invoke_mode: str | None,
) -> tuple[dict[str, Any], str] | None:
    if not peer_mcp_enabled():
        return None
    portable_id = str(meta.get("portable_id") or "")
    if not portable_id:
        return None
    try:
        output, peer_node_id = await try_peer_mcp_invoke(
            portable_id=portable_id,
            arguments=arguments,
            invoke_mode=invoke_mode or "stub",
        )
        return output, peer_node_id
    except PeerMcpError:
        return None


async def _resolve_output(
    *,
    tool_entity: Entity,
    meta: dict[str, Any],
    server_entity: Entity | None,
    arguments: dict[str, Any],
    external_result: dict[str, Any] | None,
    force_mode: str | None,
) -> tuple[dict[str, Any], str, str, str | None]:
    """Return (output, invoke_mode, model_provider, peer_node_id)."""
    server_meta = server_entity.metadata_ if server_entity else {}
    server_transport = server_meta.get("mcp_transport") if server_entity else None
    tool_name = str(meta.get("mcp_tool_name") or tool_entity.name)

    if external_result is not None:
        return _normalize_external_result(external_result), "external", MCP_EXTERNAL_PROVIDER, None

    if force_mode == "peer" or (peer_mcp_prefer_peer() and force_mode not in ("stub", "live")):
        try:
            output, peer_node_id = await try_peer_mcp_invoke(
                portable_id=str(meta.get("portable_id") or ""),
                arguments=arguments,
                invoke_mode="peer",
            )
            return output, "peer", MCP_PEER_PROVIDER, peer_node_id
        except PeerMcpError as exc:
            if force_mode == "peer":
                raise HTTPException(status_code=502, detail=str(exc)) from exc

    want_live = force_mode == "live" or (
        force_mode != "stub" and force_mode != "peer" and _live_invoke_enabled(meta, server_meta)
    )
    if want_live:
        if not server_entity or not server_transport:
            peer_result = await _try_peer_output(meta=meta, arguments=arguments, invoke_mode="live")
            if peer_result:
                output, peer_node_id = peer_result
                return output, "peer", MCP_PEER_PROVIDER, peer_node_id
            raise HTTPException(status_code=400, detail="Live MCP invoke requires linked server transport")
        runtime = meta.get("runtime") or {}
        timeout = runtime.get("timeout") or (server_meta.get("runtime") or {}).get("timeout")
        try:
            output = await wire_call_mcp_tool(
                server_transport,
                tool_name=tool_name,
                arguments=arguments,
                timeout=float(timeout) if timeout is not None else None,
            )
            return output, "live", MCP_LIVE_PROVIDER, None
        except McpClientError as exc:
            peer_result = await _try_peer_output(meta=meta, arguments=arguments, invoke_mode="live")
            if peer_result:
                output, peer_node_id = peer_result
                return output, "peer", MCP_PEER_PROVIDER, peer_node_id
            fallback = (meta.get("runtime") or {}).get("fallback_stub") or (
                (server_meta.get("runtime") or {}).get("fallback_stub")
            )
            if fallback:
                stub = _build_stub_output(
                    tool_entity=tool_entity,
                    meta=meta,
                    server_entity=server_entity,
                    arguments=arguments,
                )
                stub["content"].insert(
                    0,
                    {"type": "text", "text": f"[PoCP MCP live failed: {exc}]"},
                )
                return stub, "stub", MCP_STUB_PROVIDER, None
            raise HTTPException(status_code=502, detail=f"MCP live invoke failed: {exc}") from exc

    output = _build_stub_output(
        tool_entity=tool_entity,
        meta=meta,
        server_entity=server_entity,
        arguments=arguments,
    )
    return output, "stub", MCP_STUB_PROVIDER, None


def _build_step_metadata(
    *,
    chain_len: int,
    agent_entity_id: str | None,
    tool_entity: Entity,
    meta: dict[str, Any],
    server_entity: Entity | None,
    invoke_mode: str,
    provider: str,
    peer_node_id: str | None,
    arguments: dict[str, Any],
) -> list[dict | None]:
    """Parallel metadata for each InvocationStep in the MCP chain."""
    mcp_meta = {
        "capability_kind": "tool",
        "mcp_spec_version": meta.get("mcp_spec_version") or MCP_SPEC_VERSION,
        "mcp_tool_name": meta.get("mcp_tool_name"),
        "mcp_server_id": meta.get("mcp_server_id"),
        "invoke_mode": invoke_mode,
        "provider": provider,
        "peer_node_id": peer_node_id,
        "portable_id": meta.get("portable_id"),
    }
    invoke_meta = {
        **mcp_meta,
        "capability_kind": "tool",
        "action": "invoke_mcp",
        "arguments_preview": _arguments_summary(arguments)[:512],
    }
    if agent_entity_id:
        return [None, mcp_meta, invoke_meta]
    return [mcp_meta, invoke_meta]


def _build_invoke_response(
    *,
    tool_entity: Entity,
    meta: dict[str, Any],
    server_entity: Entity | None,
    agent_entity_id: str | None,
    arguments: dict[str, Any],
    output: dict[str, Any],
    invoke_mode: str,
    trace: InvocationTrace,
    db: Session,
    peer_node_id: str | None = None,
) -> dict[str, Any]:
    trace_loaded = _load_trace(db, trace.id)
    entities: dict[str, Entity] = {tool_entity.id: tool_entity}
    if server_entity:
        entities[server_entity.id] = server_entity
    response_text = _output_text(output)
    arg_summary = _arguments_summary(arguments)
    capability_receipts = []
    for step in sorted(trace_loaded.steps, key=lambda s: s.step_order):
        target = entities.get(step.target_entity_id) or tool_entity
        if step.action in ("invokes_mcp", "invokes_peer_mcp"):
            capability_receipts.append(
                build_capability_receipt(
                    trace_id=trace.id,
                    step=step,
                    target_entity=target,
                    request_summary=arg_summary,
                    response_summary=response_text or None,
                    extra={"invoke_mode": invoke_mode, "provider": trace.model_provider},
                )
            )
        else:
            capability_receipts.append(
                build_capability_receipt(
                    trace_id=trace.id,
                    step=step,
                    target_entity=target,
                    extra={"invoke_mode": invoke_mode, "mcp_spec_version": meta.get("mcp_spec_version")},
                )
            )
    notes = {
        "stub": "Stub invoke records InvocationTrace; enable ENABLE_MCP_LIVE_INVOKE or runtime.live for wire calls.",
        "live": "Live MCP wire protocol invoke; attach trace_id to contribution evidence.",
        "external": "External runtime reported result; attach trace_id to contribution evidence.",
        "peer": "Federated MCP invoke routed to trusted peer node; attach trace_id to contribution evidence.",
    }
    response = {
        "execution_type": "mcp_tool",
        "invoke_mode": invoke_mode,
        "tool_entity_id": tool_entity.id,
        "tool_name": tool_entity.name,
        "mcp_tool_name": meta.get("mcp_tool_name"),
        "mcp_server_id": meta.get("mcp_server_id"),
        "mcp_server_entity_id": server_entity.id if server_entity else None,
        "mcp_transport": (server_entity.metadata_ or {}).get("mcp_transport") if server_entity else None,
        "agent_entity_id": agent_entity_id,
        "arguments": arguments,
        "output": output,
        "trace_id": trace.id,
        "invocation_chain": [
            {
                "step_order": step.step_order,
                "source_entity_id": step.source_entity_id,
                "target_entity_id": step.target_entity_id,
                "action": step.action,
                "metadata": step.metadata_ or {},
            }
            for step in sorted(trace_loaded.steps, key=lambda s: s.step_order)
        ],
        "capability_receipts": capability_receipts,
        "receipt_url": f"/api/v1/invocations/{trace.id}/receipt",
        "advisory_only": True,
        "note": notes.get(invoke_mode, notes["stub"]),
    }
    if peer_node_id:
        response["peer_node_id"] = peer_node_id
        response["peer_route"] = True
    return response


async def invoke_mcp_tool(
    db: Session,
    *,
    human_entity_id: str,
    tool_entity_id: str,
    arguments: dict[str, Any] | None = None,
    agent_entity_id: str | None = None,
    task_id: str | None = None,
    contribution_id: str | None = None,
    external_result: dict[str, Any] | None = None,
    force_mode: str | None = None,
) -> dict[str, Any]:
    """Record Human → [Agent] → MCP Tool → Server chain; stub, live, or external result."""
    _require_human(db, human_entity_id)
    tool_entity, meta = _require_mcp_tool(db, tool_entity_id)
    server_entity = _resolve_server_entity(db, meta)
    args = arguments or {}

    output, invoke_mode, provider, peer_node_id = await _resolve_output(
        tool_entity=tool_entity,
        meta=meta,
        server_entity=server_entity,
        arguments=args,
        external_result=external_result,
        force_mode=force_mode,
    )

    chain_len = 3 if agent_entity_id else 2
    step_meta = _build_step_metadata(
        chain_len=chain_len,
        agent_entity_id=agent_entity_id,
        tool_entity=tool_entity,
        meta=meta,
        server_entity=server_entity,
        invoke_mode=invoke_mode,
        provider=provider,
        peer_node_id=peer_node_id,
        arguments=args,
    )

    trace = _record_mcp_trace(
        db,
        human_id=human_entity_id,
        tool_entity_id=tool_entity.id,
        server_entity_id=server_entity.id if server_entity else None,
        agent_entity_id=agent_entity_id,
        task_id=task_id,
        contribution_id=contribution_id,
        model_provider=provider,
        status=InvocationStatus.completed,
        peer_node_id=peer_node_id,
        step_metadata=step_meta,
    )

    return _build_invoke_response(
        tool_entity=tool_entity,
        meta=meta,
        server_entity=server_entity,
        agent_entity_id=agent_entity_id,
        arguments=args,
        output=output,
        invoke_mode=invoke_mode,
        trace=trace,
        db=db,
        peer_node_id=peer_node_id,
    )
