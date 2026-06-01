"""Federation pilot preflight — trust bundle + validate-proof before import/sync.

Default: Node A http://127.0.0.1:8100, Node B http://127.0.0.1:8101

Usage:
  python backend/scripts/federation_pilot_preflight.py
  python backend/scripts/federation_pilot_preflight.py http://127.0.0.1:8100 http://127.0.0.1:8101
  python backend/scripts/federation_pilot_preflight.py --sync   # preflight then POST /federation/sync on B
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

NODE_A = "http://127.0.0.1:8100"
NODE_B = "http://127.0.0.1:8101"


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


def run_preflight(node_a: str, node_b: str, *, do_sync: bool = False) -> dict:
    """Return summary dict; raises AssertionError on hard failure."""
    health_a = req(node_a, "GET", "/health")
    health_b = req(node_b, "GET", "/health")
    assert health_a.get("status") == "ok", health_a
    assert health_b.get("status") == "ok", health_b
    print(f"OK health A={health_a.get('version')} B={health_b.get('version')}")

    node_a_info = req(node_a, "GET", "/api/v1/federation/node")
    node_b_info = req(node_b, "GET", "/api/v1/federation/node")
    assert node_a_info.get("node_id") == "node-a", node_a_info
    assert node_b_info.get("node_id") == "node-b", node_b_info
    print(f"OK federation nodes A={node_a_info['node_id']} B={node_b_info['node_id']}")

    bundle_a = req(node_a, "GET", "/api/v1/federation/trust-policy-bundle")
    bundle_b = req(node_b, "GET", "/api/v1/federation/trust-policy-bundle")
    assert bundle_a.get("schema") == "pocp.trust_policy_bundle.v0.1", bundle_a
    assert bundle_b.get("schema") == "pocp.trust_policy_bundle.v0.1", bundle_b
    fp_a = bundle_a.get("bundle_fingerprint")
    fp_b = bundle_b.get("bundle_fingerprint")
    if fp_a != fp_b:
        print(f"WARN trust bundle fingerprint differs A={fp_a} B={fp_b}")
    else:
        print(f"OK trust bundle fingerprint aligned ({fp_a})")

    trust_b = req(node_b, "GET", "/api/v1/federation/trust")
    trusted_ids = {n.get("node_id") for n in trust_b.get("trusted_nodes") or []}
    assert "node-a" in trusted_ids, trust_b
    print(f"OK Node B trusts node-a (source={trust_b.get('source')})")

    approved = approved_contribution_ids(node_a)
    assert approved, "Node A has no approved contributions — wait for seed or run smoke_test"
    contribution_id = approved[0]
    proof = req(node_a, "GET", f"/api/v1/contributions/{contribution_id}/proof")
    assert proof.get("proof_type") == "pocp_contribution_proof", proof
    print(f"OK fetched proof from Node A ({contribution_id[:12]}…)")

    validation = req(
        node_b,
        "POST",
        "/api/v1/federation/validate-proof",
        {"source_node_id": "node-a", "proof": proof},
    )
    assert validation.get("blocking_valid") is True, validation
    failed = validation.get("failed_count", 0)
    print(
        f"OK validate-proof blocking_valid "
        f"checks={validation.get('check_count')} failed={failed}"
    )
    if failed:
        print(f"  advisory failures (non-blocking): {failed}")

    sync_summary = None
    if do_sync:
        sync_summary = req(node_b, "POST", "/api/v1/federation/sync")
        assert sync_summary.get("errors", 0) == 0, sync_summary
        print(
            f"OK federation sync imported={sync_summary.get('imported')} "
            f"skipped={sync_summary.get('skipped')}"
        )

    return {
        "node_a": node_a,
        "node_b": node_b,
        "contribution_id": contribution_id,
        "bundle_fingerprint_a": fp_a,
        "bundle_fingerprint_b": fp_b,
        "validation": validation,
        "sync": sync_summary,
    }


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    flags = [a for a in sys.argv[1:] if a.startswith("-")]
    node_a = args[0] if len(args) > 0 else NODE_A
    node_b = args[1] if len(args) > 1 else NODE_B
    do_sync = "--sync" in flags

    summary = run_preflight(node_a, node_b, do_sync=do_sync)
    print(
        "OK federation pilot preflight: trust bundle + validate-proof "
        + ("+ sync" if do_sync else "(dry-run only)")
    )
    if not do_sync:
        print("  Tip: re-run with --sync to import after preflight, or use federation_demo_test.py")


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
