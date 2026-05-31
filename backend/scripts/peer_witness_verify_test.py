#!/usr/bin/env python3
"""Peer witness end-to-end: submit → auto-verify → consensus includes peer:{node_id}.

Requires federation stack with ENABLE_PEER_COMPUTE on Node A:
  docker compose -f docker-compose.federation.yml up -d

Usage:
  python backend/scripts/peer_witness_verify_test.py
  python backend/scripts/peer_witness_verify_test.py http://127.0.0.1:8100
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8100"


def req(method: str, path: str, body: dict | None = None, token: str | None = None) -> dict | list:
    headers = {"Content-Type": "application/json"} if body else {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode() if body else None
    request = urllib.request.Request(
        f"{BASE.rstrip('/')}{path}",
        data=data,
        method=method,
        headers=headers,
    )
    with urllib.request.urlopen(request, timeout=90) as response:
        return json.loads(response.read().decode())


def main() -> int:
    print(f"Peer witness verify test @ {BASE}")

    status = req("GET", "/api/v1/intelligence/compute/status")
    assert status.get("peer_compute_enabled"), "ENABLE_PEER_COMPUTE not set on this node"
    print("OK peer_compute_enabled")

    login = req("POST", "/api/v1/auth/dev-login", {"username": "rain", "email": "rain@example.com"})
    token = login["access_token"]
    entity_id = login["entity"]["id"]
    print("OK dev-login")

    tasks = req("GET", "/api/v1/tasks", token=token)
    assert tasks, "No tasks — run seed on this node"
    task_id = tasks[0]["id"]

    contrib = req(
        "POST",
        "/api/v1/contributions",
        {
            "task_id": task_id,
            "primary_entity_id": entity_id,
            "contribution_type": "knowledge",
            "description": "Peer witness E2E test contribution",
            "evidence": {"summary": "Automated federated compute verification test"},
            "participants": [{"entity_id": entity_id, "role": "creator", "weight": 1.0}],
        },
        token=token,
    )
    cid = contrib["id"]
    print(f"OK submitted contribution {cid[:8]}…")

    verify = req("POST", f"/api/v1/contributions/{cid}/auto-verify", token=token)
    consensus = verify.get("consensus") or {}
    providers = [r.get("provider") for r in consensus.get("provider_results") or []]
    peer_providers = [p for p in providers if p and str(p).startswith("peer:")]
    print("providers:", providers)
    assert peer_providers, f"No peer:* witness in consensus — check trusted nodes & POCP_ALLOW_PEER_WITNESS on peer"
    print(f"OK peer witnesses: {peer_providers}")
    print(f"status={verify.get('status')} passed={consensus.get('passed')}")
    print("PASS peer witness verify E2E")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except urllib.error.HTTPError as exc:
        print(f"HTTP {exc.code}: {exc.read().decode()}", file=sys.stderr)
        raise SystemExit(1)
