"""Strict-mode federation pilot — validate all approved proofs under POCP_STRICT_TRUST_POLICY.

Simulates strict validation locally (all failed checks block) and verifies Node B
when the federation strict overlay is active.

Usage:
  python backend/scripts/federation_strict_mode_test.py
  python backend/scripts/federation_strict_mode_test.py http://127.0.0.1:8100 http://127.0.0.1:8101

With strict Node B:
  docker compose -f docker-compose.federation.yml -f docker-compose.federation.strict.yml up -d backend-b
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

from services.trust_policy_bundle import (
    clear_trust_policy_bundle_cache,
    validate_proof_against_trust_policy,
)

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
        cid = (record.get("payload") or {}).get("contribution_id")
        if cid:
            ids.append(cid)
    return ids


def validate_all_strict_local(proofs: list[tuple[str, dict]]) -> list[dict]:
    os.environ["POCP_STRICT_TRUST_POLICY"] = "true"
    clear_trust_policy_bundle_cache()
    failures: list[dict] = []
    for cid, proof in proofs:
        result = validate_proof_against_trust_policy(
            proof,
            source_node_id="node-a",
            raise_on_block=False,
        )
        if not result.get("blocking_valid"):
            failures.append(
                {
                    "contribution_id": cid,
                    "blocking_failed_count": result.get("blocking_failed_count"),
                    "checks": [c for c in result.get("checks", []) if not c.get("ok")],
                }
            )
    os.environ.pop("POCP_STRICT_TRUST_POLICY", None)
    clear_trust_policy_bundle_cache()
    return failures


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    node_a = args[0] if len(args) > 0 else NODE_A
    node_b = args[1] if len(args) > 1 else NODE_B

    assert req(node_a, "GET", "/health")["status"] == "ok"
    assert req(node_b, "GET", "/health")["status"] == "ok"
    print(f"OK health A+B")

    bundle_b = req(node_b, "GET", "/api/v1/federation/trust-policy-bundle")
    strict_active = bundle_b.get("strict_mode_active") is True
    print(
        f"OK Node B trust bundle fingerprint={bundle_b.get('bundle_fingerprint')} "
        f"strict_mode_active={strict_active}"
    )

    approved = approved_contribution_ids(node_a)
    assert approved, "Node A has no approved contributions"
    proofs = [(cid, req(node_a, "GET", f"/api/v1/contributions/{cid}/proof")) for cid in approved]
    print(f"OK loaded {len(proofs)} approved proof(s) from Node A")

    local_failures = validate_all_strict_local(proofs)
    assert not local_failures, f"Strict local validation failed for {len(local_failures)} proof(s): {local_failures[:2]}"
    print(f"OK strict local validation passed for all {len(proofs)} proof(s)")

    sample_id, sample_proof = proofs[0]
    api_validation = req(
        node_b,
        "POST",
        "/api/v1/federation/validate-proof",
        {"source_node_id": "node-a", "proof": sample_proof},
    )
    assert api_validation.get("blocking_valid") is True, api_validation
    print(
        f"OK Node B validate-proof (server strict={strict_active}) "
        f"checks={api_validation.get('check_count')} failed={api_validation.get('failed_count', 0)}"
    )

    if strict_active:
        sync = req(node_b, "POST", "/api/v1/federation/sync")
        assert sync.get("errors", 0) == 0, sync
        print(
            f"OK strict Node B sync imported={sync.get('imported')} skipped={sync.get('skipped')}"
        )
    else:
        print("  Tip: enable strict Node B with:")
        print("    docker compose -f docker-compose.federation.yml -f docker-compose.federation.strict.yml up -d backend-b")

    print("OK federation strict-mode pilot: all approved proofs pass under strict trust policy")


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
