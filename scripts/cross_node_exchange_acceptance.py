#!/usr/bin/env python3
"""CIP-P2.1 — cross-node quote→invoke→receipt over federation Docker A/B.

Validates peer dialogue routing from Node A and exchange_settled on the originator.

Usage:
  docker compose -f docker-compose.federation.yml up -d --build
  python scripts/cross_node_exchange_acceptance.py
  python scripts/cross_node_exchange_acceptance.py http://127.0.0.1:8100 http://127.0.0.1:8101
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
import uuid

NODE_A = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8100"
NODE_B = sys.argv[2] if len(sys.argv) > 2 else "http://127.0.0.1:8101"
DIALOGUE_SCHEMA = "pocp.entity_dialogue.v0.1"


def req(
    base: str,
    method: str,
    path: str,
    body: dict | None = None,
    token: str | None = None,
) -> dict | list:
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
    with urllib.request.urlopen(request, timeout=180) as response:
        return json.loads(response.read().decode())


def pick_remote_skill(node_b: str) -> dict:
    registry = req(node_b, "GET", "/api/v1/registry/capabilities?limit=50")
    items = registry.get("items") or registry.get("capabilities") or []
    for item in items:
        if item.get("entity_type") == "skill" and item.get("entity_id"):
            return item
    entities = req(node_b, "GET", "/api/v1/entities?entity_type=skill&limit=50")
    rows = entities if isinstance(entities, list) else entities.get("items") or []
    for row in rows:
        if row.get("entity_type") == "skill" and row.get("id"):
            return {
                "entity_id": row["id"],
                "portable_id": (row.get("metadata") or {}).get("portable_id"),
                "name": row.get("name"),
            }
    raise AssertionError("No skill entity on Node B — seed catalog before acceptance")


def ledger_exchange_rows(node_a: str, exchange_id: str) -> list[dict]:
    export = req(node_a, "GET", "/api/v1/ledger/export")
    rows = []
    for record in export.get("records", []):
        if record.get("event_type") != "exchange_settled":
            continue
        payload = record.get("payload") or {}
        if payload.get("exchange_id") == exchange_id or payload.get("peer_exchange_id") == exchange_id:
            rows.append(payload)
        elif payload.get("peer_route") and exchange_id in json.dumps(payload):
            rows.append(payload)
    return rows


def main() -> None:
    assert req(NODE_A, "GET", "/health")["status"] == "ok"
    assert req(NODE_B, "GET", "/health")["status"] == "ok"
    print("OK both nodes healthy")

    node_a = req(NODE_A, "GET", "/api/v1/federation/node")
    node_b = req(NODE_B, "GET", "/api/v1/federation/node")
    assert node_a["node_id"] == "node-a", node_a
    assert node_b["node_id"] == "node-b", node_b
    print(f"OK federation nodes {node_a['node_id']} → {node_b['node_id']}")

    dev_identity = {"username": "cross_node_exchange", "email": "cross_node_exchange@example.com"}
    consumer_portable_id = f"dev:{dev_identity['email']}"

    login = req(NODE_A, "POST", "/api/v1/auth/dev-login", dev_identity)
    token = login["access_token"]
    human_id = login["entity"]["id"]
    print(f"OK Node A dev-login entity={human_id[:12]}…")

    req(NODE_B, "POST", "/api/v1/auth/dev-login", dev_identity)
    print(f"OK Node B dev-login portable_id={consumer_portable_id}")

    skill = pick_remote_skill(NODE_B)
    skill_id = skill["entity_id"]
    skill_portable_id = skill.get("portable_id") or (
        f"pocp:{node_b['node_id']}:skill:{skill.get('name', 'remote')}"
    )
    print(f"OK remote skill on B: {skill.get('name', skill_id)[:40]} portable_id={skill_portable_id}")

    dialogue_base = {
        "schema": DIALOGUE_SCHEMA,
        "from": {
            "node_id": node_a["node_id"],
            "portable_id": consumer_portable_id,
        },
        "to": {
            "entity_id": skill_id,
            "node_id": node_b["node_id"],
            "portable_id": skill_portable_id,
        },
        "payload": {"route_peer": True, "input": "Cross-node exchange acceptance ping."},
    }

    quote_id = f"dlg_xn_quote_{uuid.uuid4().hex[:10]}"
    quote = req(
        NODE_A,
        "POST",
        "/api/v1/intelligence/dialogue",
        {
            **dialogue_base,
            "dialogue_id": quote_id,
            "kind": "quote",
            "payload": {
                **dialogue_base["payload"],
                "quote_action": "capability_invoke",
            },
        },
        token=token,
    )
    assert quote.get("status") == "accepted", quote
    assert quote.get("result", {}).get("peer_route") is True, quote
    exchange_id = (quote.get("refs") or {}).get("exchange_id") or (quote.get("result") or {}).get("exchange_id")
    originator_ex = (quote.get("refs") or {}).get("originator_exchange_id")
    assert exchange_id, f"quote missing exchange_id: {quote}"
    assert originator_ex or quote.get("result", {}).get("originator_exchange_settled"), quote
    print(f"OK cross-node quote exchange_id={exchange_id[:18]}… originator={str(originator_ex)[:18]}…")

    invoke_id = f"dlg_xn_invoke_{uuid.uuid4().hex[:10]}"
    invoke = req(
        NODE_A,
        "POST",
        "/api/v1/intelligence/dialogue",
        {
            **dialogue_base,
            "dialogue_id": invoke_id,
            "kind": "invoke",
            "refs": {"exchange_id": exchange_id},
            "payload": {
                **dialogue_base["payload"],
                "execute": False,
            },
        },
        token=token,
    )
    assert invoke.get("status") == "accepted", invoke
    assert invoke.get("result", {}).get("peer_route") is True, invoke
    trace_id = (invoke.get("refs") or {}).get("invocation_trace_id")
    assert trace_id, f"invoke missing local invocation_trace_id: {invoke}"
    invoke_originator = (invoke.get("refs") or {}).get("originator_exchange_id")
    assert invoke_originator or invoke.get("result", {}).get("originator_exchange_settled"), invoke
    print(f"OK cross-node invoke trace={trace_id[:12]}… originator_exchange={str(invoke_originator)[:18]}…")

    check_id = originator_ex or invoke_originator or exchange_id
    ledger_rows = ledger_exchange_rows(NODE_A, check_id)
    assert any(r.get("peer_route") for r in ledger_rows), (
        f"No peer_route exchange_settled on Node A for {check_id}; export sample empty"
    )
    print(f"OK Node A ledger exchange_settled peer_route rows={len(ledger_rows)}")

    elc = req(NODE_A, "GET", f"/api/v1/entities/{human_id}/local-chain?limit=20")
    elc_ids = {r.get("ref_id") for r in elc.get("records", [])}
    assert check_id in elc_ids or exchange_id in elc_ids, elc
    print("OK ELC lists originator exchange on Node A")

    print(
        "OK CIP-P2.1 cross-node acceptance: quote→invoke→receipt trace + exchange_settled on originator"
    )


if __name__ == "__main__":
    try:
        main()
    except urllib.error.HTTPError as exc:
        print(f"HTTP {exc.code}: {exc.read().decode()}", file=sys.stderr)
        sys.exit(1)
    except AssertionError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        sys.exit(1)
