"""Run end-to-end PoCP loop against a running API (default http://127.0.0.1:8000)."""

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
        f"{BASE}{path}",
        data=data,
        method=method,
        headers=headers,
    )
    with urllib.request.urlopen(request) as response:
        return json.loads(response.read().decode())


def main() -> None:
    health = req("GET", "/health")
    assert health["status"] == "ok", health
    print(f"OK health {health.get('version', '?')}")

    login = req(
        "POST",
        "/api/v1/auth/dev-login",
        {"username": "alice", "email": "alice@pocp.local"},
    )
    token = login["access_token"]
    assert login["entity"]["name"] == "Alice", login["entity"]
    print("OK Alice dev-login")

    me = req("GET", "/api/v1/me", token=token)
    assert me["entity"]["entity_type"] == "human"
    entity_id = me["entity"]["id"]
    print(f"OK /me entity={me['entity']['name']}")

    chat = req(
        "POST",
        "/api/v1/ai/chat",
        {"message": "What is a contribution event?", "provider": "mock"},
        token=token,
    )
    assert chat["credits_spent"] == 5
    assert chat["remaining_credits"] == 95
    print("OK ai/chat burns credits")

    usage = req("GET", "/api/v1/ai/usage", token=token)
    assert len(usage) >= 1
    print("OK ai/usage log")

    entities = req("GET", "/api/v1/entities")
    humans = [e for e in entities if e["entity_type"] == "human"]
    skills = [e for e in entities if e["entity_type"] == "skill"]
    agents = [e for e in entities if e["entity_type"] == "agent"]
    orgs = [e for e in entities if e["entity_type"] == "organization"]
    llms = {e["name"] for e in entities if e["entity_type"] == "llm"}
    assert len(humans) >= 2 and skills and agents, "Seed data missing; restart backend with empty DB"
    assert {"Lumen-0", "DeSui"}.issubset(llms), f"Genesis LLMs missing: {llms}"
    pocp_commons = next((e for e in orgs if e["name"] == "PoCP AI Commons"), None)
    assert pocp_commons, "Seed organization missing"

    try:
        req(
            "POST",
            "/api/v1/tasks",
            {
                "title": "Unauthorized sponsor task",
                "description": "Should be rejected",
                "sponsor_id": pocp_commons["id"],
            },
            token=token,
        )
        raise AssertionError("Alice should not be able to create tasks for Bob-governed organization")
    except urllib.error.HTTPError as exc:
        assert exc.code == 403

    bob_login = req(
        "POST",
        "/api/v1/auth/dev-login",
        {"username": "bob", "email": "bob@pocp.local"},
    )
    bob_token = bob_login["access_token"]
    bob_entity_id = bob_login["entity"]["id"]
    assert bob_login["entity"]["name"] == "Bob", bob_login["entity"]
    print("OK Bob dev-login")

    task = req(
        "POST",
        "/api/v1/tasks",
        {
            "title": "Smoke test task",
            "description": "Automated loop verification",
            "sponsor_id": pocp_commons["id"],
        },
        token=bob_token,
    )

    contrib = req(
        "POST",
        "/api/v1/contributions",
        {
            "task_id": task["id"],
            "primary_entity_id": entity_id,
            "contribution_type": "knowledge",
            "description": "Smoke test contribution with enough detail for mock verifier scoring.",
            "evidence": {"content_preview": "automated test evidence"},
            "participants": [
                {"entity_id": entity_id, "role": "creator", "weight": 0.4},
                {"entity_id": agents[0]["id"], "role": "executor", "weight": 0.25},
                {"entity_id": skills[0]["id"], "role": "skill_provider", "weight": 0.15},
            ],
        },
        token=token,
    )
    assert contrib["status"] == "submitted"

    try:
        req(
            "POST",
            f"/api/v1/contributions/{contrib['id']}/verify",
            {
                "model_provider": "Lumen-0",
                "score": 1.0,
                "feedback": "attempted bypass",
            },
            token=token,
        )
        raise AssertionError("Manual verify should be disabled by default")
    except urllib.error.HTTPError as exc:
        assert exc.code == 403

    auto = req("POST", f"/api/v1/contributions/{contrib['id']}/auto-verify", token=token)
    assert auto["status"] in ("ai_verified", "submitted")
    assert "consensus" in auto
    print(f"OK auto-verify status={auto['status']}")

    try:
        req(
            "POST",
            f"/api/v1/contributions/{contrib['id']}/approve",
            {"reviewer_id": entity_id, "feedback": "self approve"},
            token=token,
        )
        raise AssertionError("Self-approval should be rejected")
    except urllib.error.HTTPError as exc:
        assert exc.code == 400

    approved = req(
        "POST",
        f"/api/v1/contributions/{contrib['id']}/approve",
        {"reviewer_id": bob_entity_id, "feedback": "Smoke test approved"},
        token=bob_token,
    )
    assert approved["status"] == "approved"

    ledger = req("GET", "/api/v1/ledger")
    assert any(r["event_type"] == "contribution_approved" for r in ledger)

    verify = req("GET", "/api/v1/ledger/verify")
    assert verify["valid"] is True, verify
    assert verify["count"] >= 1
    print("OK ledger hash chain verify")

    portable = req("GET", f"/api/v1/entities/{entity_id}/portable")
    assert portable["entity"]["id"] == entity_id
    assert portable["portable_id"] == "dev:alice@pocp.local"
    print(f"OK portable entity {portable['portable_id']}")

    node = req("GET", "/api/v1/federation/node")
    assert node["spec_version"] == "0.1"
    print(f"OK federation node {node['node_id']}")

    assert contrib["evidence"].get("_pocp", {}).get("content_hash"), "evidence should be content-hashed"

    print("OK Sprint Alpha loop: login → chat → auto-verify → approve → ledger → federation")


if __name__ == "__main__":
    main()
