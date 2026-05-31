"""Two-node exchange proof federation demo (Phase 3/4).

Node A: metered invoke → exchange proof
Node B: L1 import (verify + advisory record, no BC mint)

Usage:
  docker compose -f docker-compose.federation.yml up -d --build
  python backend/scripts/federation_exchange_demo_test.py
  python backend/scripts/federation_exchange_demo_test.py http://127.0.0.1:8100 http://127.0.0.1:8101
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

NODE_A = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8100"
NODE_B = sys.argv[2] if len(sys.argv) > 2 else "http://127.0.0.1:8101"


def req(base: str, method: str, path: str, body: dict | None = None, token: str | None = None) -> dict | list:
    headers = {"Content-Type": "application/json"} if body else {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode() if body else None
    request = urllib.request.Request(
        f"{base.rstrip('/')}{path}",
        data=data,
        method=method,
        headers=headers,
    )
    with urllib.request.urlopen(request, timeout=180) as response:
        return json.loads(response.read().decode())


def main() -> None:
    health_a = req(NODE_A, "GET", "/health")
    health_b = req(NODE_B, "GET", "/health")
    assert health_a["status"] == "ok", health_a
    assert health_b["status"] == "ok", health_b
    print("OK both nodes healthy")

    node_a = req(NODE_A, "GET", "/api/v1/federation/node")
    node_b = req(NODE_B, "GET", "/api/v1/federation/node")
    assert node_a["node_id"] == "node-a", node_a
    assert node_b["node_id"] == "node-b", node_b
    print(f"OK federation nodes {node_a['node_id']} → {node_b['node_id']}")

    login = req(
        NODE_A,
        "POST",
        "/api/v1/auth/dev-login",
        {"username": "rain", "email": "rain@example.com"},
    )
    token = login["access_token"]
    entity_id = login["entity"]["id"]
    credits_before = login["wallet"]["ai_credits"]

    chat = req(
        NODE_A,
        "POST",
        "/api/v1/ai/chat",
        {"message": "Federation exchange proof demo ping.", "provider": "mock"},
        token=token,
    )
    exchange_id = chat.get("exchange_id")
    assert exchange_id, f"chat response missing exchange_id: {chat}"
    assert chat["credits_spent"] > 0
    print(f"OK Node A chat exchange={exchange_id[:20]}… spent={chat['credits_spent']}")

    proof = req(NODE_A, "GET", f"/api/v1/exchanges/{exchange_id}/proof")
    assert proof["proof_type"] == "pocp_exchange_proof", proof.get("proof_type")
    assert proof.get("exchange_inclusion"), "missing exchange_inclusion SPV"
    verified = req(NODE_A, "POST", "/api/v1/proof/verify", {"proof": proof})
    assert verified.get("valid") is True, verified
    print("OK exchange proof verified on Node A")

    elc = req(NODE_A, "GET", f"/api/v1/entities/{entity_id}/local-chain?limit=5")
    assert any(r.get("ref_id") == exchange_id for r in elc.get("records", [])), elc
    print("OK ELC lists exchange on Node A")

    imports_before = req(NODE_B, "GET", "/api/v1/federation/imports")
    before_ids = {i["id"] for i in imports_before}

    imported = req(
        NODE_B,
        "POST",
        "/api/v1/federation/import-exchange-proof",
        {
            "source_node_id": node_a["node_id"],
            "proof": proof,
            "acceptance_level": "L1",
        },
    )
    assert imported.get("contribution_type") == "exchange" or imported.get("payload", {}).get("import_kind") == "exchange_proof", imported
    print(f"OK Node B L1 import id={imported['id'][:12]}…")

    imports_after = req(NODE_B, "GET", "/api/v1/federation/imports")
    new_rows = [i for i in imports_after if i["id"] not in before_ids]
    assert new_rows, "import not visible in federation imports list"
    assert any(
        (i.get("source_contribution_id") or "").startswith("exchange:")
        or i.get("contribution_type") == "exchange"
        for i in new_rows
    ), new_rows
    print(f"OK federation imports count={len(imports_after)}")

    again = req(
        NODE_B,
        "POST",
        "/api/v1/federation/import-exchange-proof",
        {
            "source_node_id": node_a["node_id"],
            "proof": proof,
            "acceptance_level": "L1",
        },
    )
    assert again["id"] == imported["id"], "expected idempotent import"
    print("OK idempotent re-import")

    verify_b = req(NODE_B, "GET", "/api/v1/ledger/verify")
    assert verify_b["valid"] is True, verify_b
    print(f"OK Node B ledger valid count={verify_b['count']}")

    print(
        f"OK exchange federation demo: A chat (bc {credits_before}→{chat['remaining_credits']}) "
        f"→ proof → B L1 import"
    )


if __name__ == "__main__":
    try:
        main()
    except urllib.error.HTTPError as exc:
        body = exc.read().decode()
        print(f"HTTP {exc.code}: {body}", file=sys.stderr)
        sys.exit(1)
    except AssertionError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        sys.exit(1)
