"""NN-3 StudyAgent loop: run → submit contribution → auto-verify.

Usage:
  python backend/scripts/study_agent_loop_test.py
  python backend/scripts/study_agent_loop_test.py http://127.0.0.1:8000
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
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.loads(response.read().decode())


def main() -> None:
    health = req("GET", "/health")
    assert health["status"] == "ok", health
    print("OK health")

    login = req(
        "POST",
        "/api/v1/auth/dev-login",
        {"username": "rain", "email": "rain@example.com"},
    )
    token = login["access_token"]
    entity_id = login["entity"]["id"]
    print("OK Rain dev-login")

    entities = req("GET", "/api/v1/entities")
    pocp_commons = next(e for e in entities if e["name"] == "PoCP AI Commons")

    task = req(
        "POST",
        "/api/v1/tasks",
        {
            "title": "StudyAgent loop test",
            "description": "NN-3 automated contribution from agent draft",
            "sponsor_id": pocp_commons["id"],
        },
        token=token,
    )
    print(f"OK task {task['id'][:8]}…")

    run = req(
        "POST",
        "/api/v1/intelligence/agents/study/run",
        {
            "topic": "R matrix transpose and multiplication",
            "task_id": task["id"],
            "llm_provider": "mock",
            "submit_contribution": True,
        },
        token=token,
    )

    assert run["runtime"] == "state_machine_v1", run
    assert run.get("trace_id"), run
    assert len(run.get("invocation_chain") or []) == 3, run
    assert run["invocation_chain"][-1]["action"] == "invokes_llm"

    contrib = run.get("contribution")
    assert contrib, "expected contribution when submit_contribution=true"
    assert contrib["status"] == "submitted", contrib
    assert contrib.get("evidence_hash"), contrib
    print(f"OK StudyAgent submitted contribution {contrib['id'][:8]}…")

    loaded = req("GET", f"/api/v1/contributions/{contrib['id']}", token=token)
    assert loaded["primary_entity_id"] == entity_id
    sa = (loaded.get("evidence") or {}).get("study_agent") or {}
    assert sa.get("trace_id") == run["trace_id"], sa
    print("OK evidence links invocation trace")

    auto = req("POST", f"/api/v1/contributions/{contrib['id']}/auto-verify", token=token)
    assert auto["status"] in ("ai_verified", "submitted"), auto
    print(f"OK auto-verify status={auto['status']}")

    invocations = req("GET", "/api/v1/invocations", token=token)
    linked = next((i for i in invocations if i.get("contribution_id") == contrib["id"]), None)
    assert linked, "invocation trace should link to contribution"
    print(f"OK invocation {linked['id'][:8]}… linked to contribution")

    print("OK NN-3 loop: StudyAgent → submit → evidence → auto-verify")


if __name__ == "__main__":
    try:
        main()
    except urllib.error.HTTPError as exc:
        print(f"HTTP {exc.code}: {exc.read().decode()}", file=sys.stderr)
        sys.exit(1)
    except AssertionError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        sys.exit(1)
