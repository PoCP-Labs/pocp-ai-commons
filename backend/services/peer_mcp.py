"""NN-5 extension — route MCP tool invokes to trusted peer compute nodes."""

from __future__ import annotations

import os
from typing import Any

import httpx

from services.peer_compute import (
    MCP_INVOKE_PATH,
    PeerComputeNode,
    load_peer_compute_nodes,
    select_peer_compute_node,
)

MCP_PEER_PROVIDER = "mcp-peer"


class PeerMcpError(Exception):
    """Federated MCP invoke failed on all attempted peers."""


def peer_mcp_enabled() -> bool:
    env = os.getenv("ENABLE_PEER_MCP", "").strip().lower()
    if env in ("true", "1", "yes", "on"):
        return True
    if env in ("false", "0", "no", "off"):
        return False
    from services.peer_compute import peer_compute_enabled

    return peer_compute_enabled()


def peer_mcp_prefer_peer() -> bool:
    return os.getenv("ENABLE_PEER_MCP_PREFER_PEER", "false").lower() in ("true", "1", "yes", "on")


def _normalize_remote_invoke_mode(invoke_mode: str | None) -> str:
    """Map client-side modes to what a peer node's /compute/mcp/invoke accepts."""
    mode = (invoke_mode or "stub").lower()
    if mode == "peer":
        return os.getenv("POCP_PEER_MCP_REMOTE_MODE", "stub").lower()
    if mode in ("stub", "live"):
        return mode
    return "stub"


async def invoke_mcp_on_peer(
    peer: PeerComputeNode,
    *,
    portable_id: str,
    arguments: dict[str, Any],
    invoke_mode: str | None = "live",
    source_node_id: str | None = None,
) -> dict[str, Any]:
    url = f"{peer.base_url.rstrip('/')}{MCP_INVOKE_PATH}"
    headers = {"Content-Type": "application/json"}
    from services.peer_trust import build_peer_auth_headers

    headers.update(build_peer_auth_headers(source_node_id=source_node_id))

    payload = {
        "portable_id": portable_id,
        "arguments": arguments,
        "invoke_mode": _normalize_remote_invoke_mode(invoke_mode),
        "source_node_id": source_node_id or os.getenv("POCP_NODE_ID", "local"),
    }
    timeout = float(os.getenv("POCP_PEER_MCP_TIMEOUT", os.getenv("POCP_PEER_WITNESS_TIMEOUT", "90")))
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    if not isinstance(data, dict) or "output" not in data:
        raise PeerMcpError(f"Invalid peer MCP response from {peer.node_id}")
    return {
        **data,
        "peer_node_id": peer.node_id,
        "peer_base_url": peer.base_url,
    }


async def try_peer_mcp_invoke(
    *,
    portable_id: str,
    arguments: dict[str, Any],
    invoke_mode: str | None = "live",
) -> tuple[dict[str, Any], str]:
    """Try peers in routing order; return (output, peer_node_id)."""
    if not portable_id:
        raise PeerMcpError("MCP portable_id required for peer routing")

    nodes = load_peer_compute_nodes()
    if not nodes:
        raise PeerMcpError("No peer compute nodes configured")

    errors: list[str] = []
    tried: set[str] = set()
    while len(tried) < len(nodes):
        peer = select_peer_compute_node()
        if peer is None or peer.node_id in tried:
            break
        tried.add(peer.node_id)
        try:
            result = await invoke_mcp_on_peer(
                peer,
                portable_id=portable_id,
                arguments=arguments,
                invoke_mode=invoke_mode,
            )
            return result["output"], str(result["peer_node_id"])
        except Exception as exc:
            errors.append(f"{peer.node_id}: {exc}")

    raise PeerMcpError("; ".join(errors) or "No peer MCP nodes available")
