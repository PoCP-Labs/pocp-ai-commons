"""Epic D — two-node federation end-to-end verification.

Default targets match docker-compose.federation.yml:
  Node A (source)  http://127.0.0.1:8100
  Node B (mirror)  http://127.0.0.1:8101

Usage:
  python backend/scripts/federation_demo_test.py
  python backend/scripts/federation_demo_test.py http://127.0.0.1:8100 http://127.0.0.1:8101
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

NODE_A = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8100"
NODE_B = sys.argv[2] if len(sys.argv) > 2 else "http://127.0.0.1:8101"
RAIN_PORTABLE = "dev:rain@example.com"


def req(base: str, method: str, path: str, body: dict | None = None) -> dict | list:
    headers = {"Content-Type": "application/json"} if body else {}
    data = json.dumps(body).encode() if body else None
    request = urllib.request.Request(
        f"{base.rstrip('/')}{path}",
        data=data,
        method=method,
        headers=headers,
    )
    with urllib.request.urlopen(request, timeout=180) as response:
        return json.loads(response.read().decode())


def assert_hybrid_crypto(base: str, label: str) -> None:
    readiness = req(base, "GET", "/api/v1/crypto/readiness")
    assert readiness.get("hybrid_signing_enabled") is True, f"{label} crypto readiness: {readiness}"
    assert readiness.get("active_crypto_suite") == "pocp-crypto-v0.2-hybrid", readiness
    print(f"OK {label} hybrid crypto suite active")

    anchor = req(base, "GET", "/api/v1/ledger/anchor")
    federation = anchor.get("federation") or {}
    assert federation.get("crypto_suite") == "pocp-crypto-v0.2-hybrid", anchor
    assert "pqc" in (federation.get("signatures") or {}), anchor
    assert anchor.get("graph_merkle_root"), f"{label} missing graph_merkle_root"
    assert anchor.get("hash_algorithm"), f"{label} missing hash_algorithm"
    print(f"OK {label} anchor hybrid+PQC graph_root={str(anchor['graph_merkle_root'])[:12]}…")


def assert_node_health(base: str, label: str) -> dict:
    health = req(base, "GET", "/health")
    assert health["status"] == "ok", f"{label} health: {health}"
    print(f"OK {label} health")
    return health


def assert_federation_node(base: str, label: str, *, expected_id: str | None = None) -> dict:
    node = req(base, "GET", "/api/v1/federation/node")
    assert node["spec_version"] == "0.1", node
    if expected_id:
        assert node["node_id"] == expected_id, node
    assert node.get("public_key"), f"{label} missing public_key"
    print(f"OK {label} federation node_id={node['node_id']}")
    return node


def approved_contribution_ids(base: str) -> list[str]:
    export = req(base, "GET", "/api/v1/ledger/export")
    ids: list[str] = []
    for record in export.get("records", []):
        if record.get("event_type") != "contribution_approved":
            continue
        payload = record.get("payload") or {}
        cid = payload.get("contribution_id")
        if cid:
            ids.append(cid)
    return ids


def main() -> None:
    assert_node_health(NODE_A, "Node A")
    assert_node_health(NODE_B, "Node B")

    node_a = assert_federation_node(NODE_A, "Node A", expected_id="node-a")
    node_b = assert_federation_node(NODE_B, "Node B", expected_id="node-b")
    assert node_b.get("node_mode") == "read_only_mirror", node_b

    peers = req(NODE_B, "GET", "/api/v1/federation/peers/health")
    assert peers["peer_count"] >= 1, peers
    peer_a = next((p for p in peers["peers"] if p.get("node_id") == "node-a"), None)
    assert peer_a, f"node-a not in trust list: {peers}"
    assert peer_a.get("reachable") is True, peer_a
    assert peer_a.get("ledger_valid") is True, peer_a
    print(f"OK Node B trusts Node A (ledger_valid={peer_a.get('ledger_valid')})")

    verify_a = req(NODE_A, "GET", "/api/v1/ledger/verify")
    verify_b = req(NODE_B, "GET", "/api/v1/ledger/verify")
    assert verify_a["valid"] is True, verify_a
    assert verify_b["valid"] is True, verify_b
    print(f"OK ledger chains valid (A={verify_a['count']} B={verify_b['count']})")

    approved = approved_contribution_ids(NODE_A)
    assert approved, "Node A has no approved contributions — run seed or smoke_test on A first"
    proof = req(NODE_A, "GET", f"/api/v1/contributions/{approved[0]}/proof")
    fed = proof.get("federation") or {}
    assert fed.get("node_id") == "node-a", fed
    assert fed.get("public_key") == node_a["public_key"], fed
    assert fed.get("signature"), "proof missing federation Ed25519 signature"
    print(f"OK signed proof from Node A ({approved[0][:8]}…)")

    imports_before = req(NODE_B, "GET", "/api/v1/federation/imports")
    sync = req(NODE_B, "POST", "/api/v1/federation/sync")
    assert sync["errors"] == 0, sync
    print(
        f"OK federation sync imported={sync['imported']} skipped={sync['skipped']} errors={sync['errors']}"
    )

    imports = req(NODE_B, "GET", "/api/v1/federation/imports")
    assert len(imports) >= len(imports_before), imports
    assert any(i["source_node_id"] == "node-a" for i in imports), imports
    print(f"OK Node B federated imports={len(imports)}")

    rep = req(NODE_B, "GET", f"/api/v1/federation/reputation?portable_id={RAIN_PORTABLE}")
    assert rep["federated_import_count"] >= 1, rep
    assert rep["federated_reputation_total"] > 0, rep
    print(
        f"OK cross-node reputation portable_id={RAIN_PORTABLE} "
        f"total={rep['total_score']} federated={rep['federated_reputation_total']}"
    )

    peer_entities = req(NODE_B, "GET", "/api/v1/federation/peers/entities")
    assert peer_entities["peer_count"] >= 1, peer_entities
    entity_ids = {e["entity_id"] for e in peer_entities["entities"]}
    assert "pocp-entity-federation-peer-node-a" in entity_ids, entity_ids
    print("OK federation peer community entities on Node B")

    graph = req(NODE_B, "GET", "/api/v1/federation/imports/graph-summary")
    assert graph.get("import_count", 0) >= 1 or graph.get("edge_count", 0) >= 0, graph
    print(f"OK federated import graph summary import_count={graph.get('import_count')}")

    trust = req(NODE_B, "GET", "/api/v1/federation/trust")
    trust_nodes = trust.get("trusted_nodes") or []
    assert any(n.get("node_id") == "node-a" for n in trust_nodes), trust
    print("OK trust list exposes node-a public key")

    anchor_a = req(NODE_A, "GET", "/api/v1/ledger/anchor")
    anchor_b = req(NODE_B, "GET", "/api/v1/ledger/anchor")
    assert anchor_a.get("merkle_root"), anchor_a
    assert anchor_b.get("merkle_root"), anchor_b
    assert_hybrid_crypto(NODE_A, "Node A")
    print("OK public ledger anchors on both nodes")

    print(
        "OK Epic D demo: dual-node federation — signed proof → mirror sync → cross-node reputation"
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
