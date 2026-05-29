"""Run end-to-end PoCP loop against a running API (default http://127.0.0.1:8000)."""

import json
import sys
import urllib.error
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"


def req(method: str, path: str, body: dict | None = None) -> dict | list:
    data = json.dumps(body).encode() if body else None
    request = urllib.request.Request(
        f"{BASE}{path}",
        data=data,
        method=method,
        headers={"Content-Type": "application/json"} if body else {},
    )
    with urllib.request.urlopen(request) as response:
        return json.loads(response.read().decode())


def main() -> None:
    health = req("GET", "/health")
    assert health["status"] == "ok", health
    print(f"OK health {health.get('version', '?')}")

    entities = req("GET", "/api/v1/entities")
    humans = [e for e in entities if e["entity_type"] == "human"]
    skills = [e for e in entities if e["entity_type"] == "skill"]
    agents = [e for e in entities if e["entity_type"] == "agent"]
    assert len(humans) >= 2 and skills and agents, "Seed data missing; restart backend with empty DB"

    creator, reviewer = humans[0], humans[1]
    if creator["id"] == reviewer["id"]:
        reviewer = humans[1]

    task = req(
        "POST",
        "/api/v1/tasks",
        {
            "title": "Smoke test task",
            "description": "Automated loop verification",
            "sponsor_id": creator["id"],
        },
    )

    contrib = req(
        "POST",
        "/api/v1/contributions",
        {
            "task_id": task["id"],
            "primary_entity_id": creator["id"],
            "contribution_type": "knowledge",
            "description": "Smoke test contribution",
            "evidence": {"content_preview": "automated test"},
            "participants": [
                {"entity_id": creator["id"], "role": "creator", "weight": 0.4},
                {"entity_id": agents[0]["id"], "role": "executor", "weight": 0.25},
                {"entity_id": skills[0]["id"], "role": "skill_provider", "weight": 0.15},
            ],
        },
    )
    assert contrib["status"] == "submitted"

    verified = req(
        "POST",
        f"/api/v1/contributions/{contrib['id']}/verify",
        {"model_provider": "deepseek", "score": 0.9, "feedback": "Smoke test pass"},
    )
    assert verified["status"] == "ai_verified"

    try:
        req(
            "POST",
            f"/api/v1/contributions/{contrib['id']}/approve",
            {"reviewer_id": creator["id"], "feedback": "self approve"},
        )
        raise AssertionError("Self-approval should be rejected")
    except urllib.error.HTTPError as exc:
        assert exc.code == 400

    approved = req(
        "POST",
        f"/api/v1/contributions/{contrib['id']}/approve",
        {"reviewer_id": reviewer["id"], "feedback": "Smoke test approved"},
    )
    assert approved["status"] == "approved"

    ledger = req("GET", "/api/v1/ledger")
    assert any(r["event_type"] == "contribution_approved" for r in ledger)

    print("OK full loop: submit → verify → approve → ledger")


if __name__ == "__main__":
    main()
