"""Two-node exchange proof federation demo (Phase 3/4).

Node A: metered invoke → exchange proof
Node B: L1 import (verify + advisory record, no BC mint)

Usage:
  docker compose -f docker-compose.federation.yml up -d --build
  python backend/scripts/federation_exchange_demo_test.py
  python backend/scripts/federation_exchange_demo_test.py http://127.0.0.1:8100 http://127.0.0.1:8101
  POCP_STAGING_FEDERATION_EXCHANGE=1 python backend/scripts/federation_exchange_demo_test.py \\
    https://api-a.example https://api-b.example
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[1]
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from services.federation_exchange_import import (
    is_public_federation_url,
    resolve_staging_exchange_import_peers,
    staging_exchange_import_policy,
)


def _staging_mode() -> bool:
    return os.getenv("POCP_STAGING_FEDERATION_EXCHANGE", "").lower() in ("1", "true", "yes", "on")


def _resolve_nodes() -> tuple[str, str]:
    if len(sys.argv) >= 3:
        return sys.argv[1].rstrip("/"), sys.argv[2].rstrip("/")
    if _staging_mode():
        node_a, node_b, _, _ = resolve_staging_exchange_import_peers()
        return node_a, node_b
    return "http://127.0.0.1:8100", "http://127.0.0.1:8101"


NODE_A, NODE_B = _resolve_nodes()


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


def _auth_token(node_a: str) -> tuple[str, str, int]:
    """Return (token, entity_id, credits_before). Staging uses POCP_ACCEPTANCE_BEARER_TOKEN."""
    staging_token = os.getenv("POCP_ACCEPTANCE_BEARER_TOKEN", "").strip()
    if _staging_mode() or staging_token:
        if not staging_token:
            raise AssertionError(
                "POCP_ACCEPTANCE_BEARER_TOKEN required for staging federation exchange demo"
            )
        me = req(node_a, "GET", "/api/v1/auth/me", token=staging_token)
        entity_id = (me.get("entity") or {}).get("id") or me.get("entity_id")
        wallet = me.get("wallet") or {}
        credits = wallet.get("ai_credits", 0)
        if not entity_id:
            raise AssertionError(f"staging token /auth/me missing entity: {me}")
        return staging_token, entity_id, int(credits)

    login = req(
        node_a,
        "POST",
        "/api/v1/auth/dev-login",
        {"username": "rain", "email": "rain@example.com"},
    )
    return login["access_token"], login["entity"]["id"], login["wallet"]["ai_credits"]


def main() -> None:
    if _staging_mode():
        policy = staging_exchange_import_policy()
        if not policy["public_peer_urls"]:
            print(
                "WARN staging mode but peer URLs are not public; "
                "set POCP_TRUSTED_NODES with HTTPS hosts",
                file=sys.stderr,
            )
        elif not all(is_public_federation_url(u) for u in (NODE_A, NODE_B)):
            print("WARN staging peers include loopback URLs", file=sys.stderr)

    health_a = req(NODE_A, "GET", "/health")
    health_b = req(NODE_B, "GET", "/health")
    assert health_a["status"] == "ok", health_a
    assert health_b["status"] == "ok", health_b
    print("OK both nodes healthy")

    node_a = req(NODE_A, "GET", "/api/v1/federation/node")
    node_b = req(NODE_B, "GET", "/api/v1/federation/node")
    if not _staging_mode():
        assert node_a["node_id"] == "node-a", node_a
        assert node_b["node_id"] == "node-b", node_b
    print(f"OK federation nodes {node_a['node_id']} → {node_b['node_id']}")

    token, entity_id, credits_before = _auth_token(NODE_A)

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
    assert imported.get("contribution_type") == "exchange" or imported.get("payload", {}).get(
        "import_kind"
    ) == "exchange_proof", imported
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
