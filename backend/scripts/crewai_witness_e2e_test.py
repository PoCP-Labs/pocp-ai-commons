#!/usr/bin/env python3
"""CrewAI witness E2E: submit → auto-verify → consensus includes crewai provider.

Requires backend with optional CrewAI witness:
  ENABLE_CREWAI_WITNESS=true

Usage:
  python backend/scripts/crewai_witness_e2e_test.py
  python backend/scripts/crewai_witness_e2e_test.py http://127.0.0.1:8100
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"


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


def crewai_enabled_on_server() -> bool:
    status = req("GET", "/api/v1/intelligence/status")
    for module in status.get("modules") or []:
        if module.get("module") != "verification":
            continue
        providers = module.get("providers") or []
        return "crewai" in providers
    compute = req("GET", "/api/v1/intelligence/compute/status")
    return "crewai" in (compute.get("active_adapters") or [])


def main() -> int:
    print(f"CrewAI witness E2E @ {BASE}")

    if not crewai_enabled_on_server():
        print("NOTE: ENABLE_CREWAI_WITNESS not active on this node — skipping crewai assertion (exit 0).")
        return 0

    print("OK crewai witness enabled on server")

    login = req("POST", "/api/v1/auth/dev-login", {"username": "rain", "email": "rain@example.com"})
    token = login["access_token"]
    entity_id = login["entity"]["id"]
    print("OK dev-login")

    tasks = req("GET", "/api/v1/tasks", token=token)
    assert tasks, "No tasks — seed the node first"
    task_id = tasks[0]["id"]

    contrib = req(
        "POST",
        "/api/v1/contributions",
        {
            "task_id": task_id,
            "primary_entity_id": entity_id,
            "contribution_type": "knowledge",
            "description": "CrewAI multi-agent witness E2E test contribution with evidence.",
            "evidence": {"summary": "Automated CrewAI witness verification test", "source": "crewai_witness_e2e_test.py"},
            "participants": [{"entity_id": entity_id, "role": "creator", "weight": 1.0}],
        },
        token=token,
    )
    cid = contrib["id"]
    print(f"OK submitted contribution {cid[:8]}…")

    verify = req("POST", f"/api/v1/contributions/{cid}/auto-verify", token=token)
    consensus = verify.get("consensus") or {}
    providers = [r.get("provider") for r in consensus.get("provider_results") or []]
    print("providers:", providers)

    assert "crewai" in providers, f"crewai missing from consensus — got {providers}"
    crew = next(r for r in consensus.get("provider_results") or [] if r.get("provider") == "crewai")
    assert crew.get("quality") is not None, crew
    print(f"OK crewai witness quality={crew.get('quality')} rationale={str(crew.get('rationale', ''))[:80]}…")
    print(f"status={verify.get('status')} passed={consensus.get('passed')}")
    print("PASS CrewAI witness E2E")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except urllib.error.HTTPError as exc:
        print(f"HTTP {exc.code}: {exc.read().decode()}", file=sys.stderr)
        raise SystemExit(1)
