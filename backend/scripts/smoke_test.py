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
        {"username": "rain", "email": "rain@example.com"},
    )
    token = login["access_token"]
    assert login["entity"]["name"] == "Rain", login["entity"]
    print("OK Rain dev-login")

    me = req("GET", "/api/v1/me", token=token)
    assert me["entity"]["entity_type"] == "human"
    entity_id = me["entity"]["id"]
    credits_before = me["wallet"]["ai_credits"]
    print(f"OK /me entity={me['entity']['name']}")

    chat = req(
        "POST",
        "/api/v1/ai/chat",
        {"message": "What is a contribution event?", "provider": "mock"},
        token=token,
    )
    assert chat["credits_spent"] == 5
    assert chat["remaining_credits"] == credits_before - 5, (
        f"expected {credits_before - 5}, got {chat['remaining_credits']}"
    )
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

    ontology = req("GET", "/api/v1/entities/ontology")
    assert len(ontology["entity_types"]) == 9
    assert "witness" in ontology["participant_roles"]
    assert "llm_inference" in ontology.get("compute_capabilities", [])
    print("OK entity ontology")

    compute_providers = req("GET", "/api/v1/compute/providers")
    if compute_providers.get("provider_count", 0) >= 1:
        print(f"OK compute providers={compute_providers['provider_count']}")
    else:
        print("SKIP compute providers (optional — not required for Genesis MVP)")

    tool_ids = {e["id"] for e in entities if e["entity_type"] == "tool"}
    dataset_ids = {e["id"] for e in entities if e["entity_type"] == "dataset"}
    assert "pocp-entity-r-docs-tool" in tool_ids, "Demo tool entity missing — run upgrade_demo_topology or reset DB"
    assert "pocp-entity-r-matrix-dataset" in dataset_ids, "Demo dataset entity missing"

    contributions = req("GET", "/api/v1/contributions")
    demo = next(
        (c for c in contributions if "matrix" in (c.get("description") or "").lower()),
        None,
    )
    if demo and demo.get("participants"):
        roles = {p["role"] for p in demo["participants"]}
        assert "witness" in roles, f"Demo missing witness role: {roles}"
        assert "tool_provider" in roles, f"Demo missing tool_provider: {roles}"
        assert "data_provider" in roles, f"Demo missing data_provider: {roles}"
        print(f"OK demo topology roles={len(roles)}")

    outsider = req(
        "POST",
        "/api/v1/auth/dev-login",
        {"username": "carol", "email": "carol@example.com"},
    )
    try:
        req(
            "POST",
            "/api/v1/tasks",
            {
                "title": "Unauthorized sponsor task",
                "description": "Should be rejected",
                "sponsor_id": pocp_commons["id"],
            },
            token=outsider["access_token"],
        )
        raise AssertionError("Outsider should not create tasks for PoCP AI Commons")
    except urllib.error.HTTPError as exc:
        assert exc.code == 403

    bob_login = req(
        "POST",
        "/api/v1/auth/dev-login",
        {"username": "bob", "email": "bob@example.com"},
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
        token=token,
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
    assert auto["status"] == "approved", f"expected auto-finalize to approve, got {auto['status']}"
    assert auto.get("finalization", {}).get("applied") or auto["status"] == "approved"
    assert "consensus" in auto
    print(f"OK auto-verify + auto-finalize status={auto['status']}")

    ledger = req("GET", "/api/v1/ledger")
    assert any(r["event_type"] == "contribution_approved" for r in ledger)

    verify = req("GET", "/api/v1/ledger/verify")
    assert verify["valid"] is True, verify
    assert verify["count"] >= 1
    print("OK ledger hash chain verify")

    portable = req("GET", f"/api/v1/entities/{entity_id}/portable")
    assert portable["entity"]["id"] == entity_id
    assert portable["portable_id"] == "dev:rain@example.com"
    print(f"OK portable entity {portable['portable_id']}")

    proof = req("GET", f"/api/v1/contributions/{contrib['id']}/proof")
    assert proof["proof_type"] == "pocp_contribution_proof"
    assert proof["contribution_event"]["id"] == contrib["id"]
    assert proof["integrity"]["proof_hash"]
    assert proof["integrity"]["evidence_hash"] == contrib["evidence"]["_pocp"]["content_hash"]
    assert proof.get("finalization") or proof["verification"].get("entity_finalizations"), (
        "approved contribution should include entity finalization"
    )
    assert proof["rights_and_reputation"]["credit_transactions"], "approved contribution should include rights issuance"
    print(f"OK contribution proof {proof['integrity']['proof_hash'][:12]}")

    node = req("GET", "/api/v1/federation/node")
    assert node["spec_version"] == "0.1"
    assert any("/contributions/{id}/proof" in endpoint for endpoint in node["public_endpoints"])
    print(f"OK federation node {node['node_id']}")

    assert contrib["evidence"].get("_pocp", {}).get("content_hash"), "evidence should be content-hashed"

    try:
        imported = req(
            "POST",
            "/api/v1/federation/import-proof",
            {"source_node_id": node["node_id"], "proof": proof},
        )
        assert imported["source_contribution_id"] == contrib["id"]
        assert imported["reputation_applied"] > 0
        imports = req("GET", "/api/v1/federation/imports")
        assert any(i["id"] == imported["id"] for i in imports)
        print(f"OK federation import reputation={imported['reputation_applied']}")
    except urllib.error.HTTPError as exc:
        if exc.code == 403:
            print("SKIP federation import (set POCP_ALLOW_UNTRUSTED_IMPORT=true on server)")
        elif exc.code == 409:
            print("OK federation import already present")
        else:
            raise

    print("OK Genesis MVP loop: login → chat → auto-verify → finalize → proof → ledger")


if __name__ == "__main__":
    main()
