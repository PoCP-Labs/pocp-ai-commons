"""Smoke test: capability catalog + direct Skill/Agent execution.

Usage (server running, dev login token optional):
  python backend/scripts/capability_execute_test.py
  python backend/scripts/capability_execute_test.py http://127.0.0.1:8000
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
    request = urllib.request.Request(f"{BASE}{path}", data=data, method=method, headers=headers)
    with urllib.request.urlopen(request) as response:
        return json.loads(response.read().decode())


def dev_login() -> str:
    data = req("POST", "/api/v1/auth/dev-login", {"username": "capability-test"})
    return data["access_token"]


def main() -> None:
    health = req("GET", "/health")
    assert health["status"] in ("ok", "degraded"), health
    print(f"OK health {health.get('version', '?')}")

    sources = req("GET", "/api/v1/capabilities/sources")
    slugs = {s["slug"] for s in sources.get("sources", [])}
    assert "openclaw" in slugs and "agentskills" in slugs, slugs
    print(f"OK capability sources ({len(slugs)})")

    token = dev_login()
    print("OK dev login")

    sync = req("POST", "/api/v1/capabilities/sync/bundled", {}, token=token)
    print(f"OK sync bundled ({sync.get('imported', 0)} items)")

    catalog = req("GET", "/api/v1/capabilities/catalog", token=token)
    items = catalog.get("items") or []
    skills = [i for i in items if i.get("entity_type") == "skill" and i.get("status") == "active"]
    if not skills:
        pending = [i for i in items if i.get("entity_type") == "skill" and i.get("status") == "pending"]
        if pending:
            req("POST", f"/api/v1/capabilities/{pending[0]['entity_id']}/activate", {}, token=token)
            catalog = req("GET", "/api/v1/capabilities/catalog", token=token)
            skills = [i for i in catalog.get("items", []) if i.get("entity_type") == "skill" and i.get("status") == "active"]
    assert skills, "No active skill in catalog"
    skill = skills[0]
    print(f"OK catalog skill: {skill['name']}")

    executed = req(
        "POST",
        f"/api/v1/capabilities/skills/{skill['entity_id']}/execute",
        {
            "input": "List three R matrix operations with one-line examples.",
            "llm_provider": "mock",
            "include_receipt": True,
        },
        token=token,
    )
    assert executed.get("trace_id"), executed
    assert executed.get("output"), executed
    print(f"OK skill execute trace={executed['trace_id'][:8]}… credits={executed.get('billing', {}).get('credits_spent')}")

    agents = [i for i in catalog.get("items", []) if i.get("entity_type") == "agent" and i.get("status") == "active"]
    if agents:
        agent = agents[0]
        agent_run = req(
            "POST",
            f"/api/v1/capabilities/agents/{agent['entity_id']}/execute",
            {
                "input": "Matrix transpose in R",
                "skill_entity_id": skill["entity_id"],
                "llm_provider": "mock",
            },
            token=token,
        )
        assert agent_run.get("trace_id"), agent_run
        print(f"OK agent execute trace={agent_run['trace_id'][:8]}…")
    else:
        print("SKIP agent execute (no active agent in catalog)")

    receipt = req("GET", f"/api/v1/invocations/{executed['trace_id']}/receipt", token=token)
    assert receipt.get("trace_id") == executed["trace_id"], receipt
    print("OK invocation receipt")

    print("OK capability execute smoke test complete")


if __name__ == "__main__":
    try:
        main()
    except urllib.error.HTTPError as exc:
        body = exc.read().decode()
        print(f"HTTP {exc.code}: {body[:500]}")
        sys.exit(1)
    except AssertionError as exc:
        print(f"FAIL: {exc}")
        sys.exit(1)
