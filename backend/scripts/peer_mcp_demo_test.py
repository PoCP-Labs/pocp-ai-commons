#!/usr/bin/env python3
"""Federated MCP E2E: bundled MCP tools → peer invoke with InvocationTrace.

Requires federation stack:
  docker compose -f docker-compose.federation.yml up -d
  ENABLE_PEER_MCP=true on Node A (set in compose)

Usage:
  python backend/scripts/peer_mcp_demo_test.py
  python backend/scripts/peer_mcp_demo_test.py http://127.0.0.1:8100
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

DEFAULT_BASE = "http://127.0.0.1:8100"


def req(method: str, base: str, path: str, body: dict | None = None, token: str | None = None) -> dict | list:
    headers: dict[str, str] = {}
    if body is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(
        f"{base.rstrip('/')}{path}",
        data=data,
        method=method,
        headers=headers,
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode())


def main(base: str) -> int:
    root = base.rstrip("/")
    print(f"Peer MCP E2E against {root}")

    status = req("GET", root, "/api/v1/intelligence/compute/status")
    print("peer_mcp_enabled:", status.get("peer_mcp_enabled"))
    print("mcp_invoke_endpoint:", status.get("mcp_invoke_endpoint"))

    peers = req("GET", root, "/api/v1/intelligence/compute/peers")
    print("reachable peers:", peers.get("reachable_count"), "/", peers.get("peer_count"))

    stub = req(
        "POST",
        root,
        "/api/v1/intelligence/compute/mcp/invoke",
        {
            "portable_id": "mcp:pocp-demo-fetch/fetch",
            "arguments": {"url": "https://example.com"},
            "invoke_mode": "stub",
        },
    )
    assert stub.get("output"), stub
    print("OK local peer MCP endpoint — mode:", stub.get("invoke_mode"))

    login = req("POST", root, "/api/v1/auth/dev-login", {"username": "rain", "email": "rain@example.com"})
    token = login["access_token"]
    print("OK dev-login")

    imported = req(
        "POST",
        root,
        "/api/v1/capabilities/import/mcp",
        {
            "external_id": "pocp-demo-fetch",
            "name": "MCP Fetch (demo)",
            "transport": {"command": "npx", "args": ["-y", "@modelcontextprotocol/server-fetch"]},
            "tools": [{"name": "fetch", "description": "Fetch URL for peer MCP E2E"}],
            "activate": True,
        },
        token=token,
    )
    tool_id = imported["tools"][0]["entity_id"]
    print("OK import/activate MCP fetch tool — status:", imported["tools"][0].get("status"))

    if not status.get("peer_mcp_enabled"):
        print("NOTE: ENABLE_PEER_MCP not set — user peer routing inactive (exit 0).")
        return 0

    if peers.get("reachable_count", 0) == 0:
        print("WARN: no reachable peers — cannot test invoke_mode=peer")
        return 1

    invoked = req(
        "POST",
        root,
        f"/api/v1/capabilities/mcp/{tool_id}/invoke",
        {
            "arguments": {"url": "https://example.com"},
            "invoke_mode": "peer",
        },
        token=token,
    )
    assert invoked.get("invoke_mode") == "peer", invoked
    assert invoked.get("peer_node_id"), invoked
    assert invoked.get("trace_id"), invoked
    print("OK peer MCP user invoke — peer:", invoked["peer_node_id"], "trace:", invoked["trace_id"][:8], "…")
    print("PASS federated MCP E2E")
    return 0


if __name__ == "__main__":
    base_url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_BASE
    try:
        raise SystemExit(main(base_url))
    except urllib.error.HTTPError as exc:
        print(f"HTTP {exc.code}: {exc.read().decode()}", file=sys.stderr)
        raise SystemExit(1)
