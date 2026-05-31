#!/usr/bin/env python3
"""Distributed compute Phase α demo — providers, schedule job, auto-verify schedule."""

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
    request = urllib.request.Request(f"{BASE.rstrip('/')}{path}", data=data, method=method, headers=headers)
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode())


def main() -> int:
    health = req("GET", "/health")
    assert health["status"] == "ok", health
    print(f"OK health {health.get('version', '?')}")

    status = req("GET", "/api/v1/intelligence/compute/status")
    print(f"OK compute status node={status.get('node_id')} adapters={status.get('active_adapters')}")

    providers = req("GET", "/api/v1/compute/providers")
    assert providers.get("provider_count", 0) >= 1, "Expected demo compute providers after seed"
    print(f"OK compute providers count={providers['provider_count']}")

    witness_providers = req("GET", "/api/v1/compute/providers?capability=witness")
    assert witness_providers.get("provider_count", 0) >= 1
    print(f"OK witness providers count={witness_providers['provider_count']}")

    login = req("POST", "/api/v1/auth/dev-login", {"username": "rain", "email": "rain@example.com"})
    token = login["access_token"]

    contributions = req("GET", "/api/v1/contributions")
    demo_contrib = next((c for c in contributions if "matrix" in (c.get("description") or "").lower()), None)
    contrib_id = demo_contrib["id"] if demo_contrib else None
    if not contrib_id:
        print("SKIP compute job (no demo contribution for binding)")
    else:
        job = req(
            "POST",
            "/api/v1/compute/jobs",
            {
                "capability": "llm_inference",
                "contribution_id": contrib_id,
                "constraints": {"model": "qwen2.5:7b", "input_preview": "demo"},
            },
            token=token,
        )
        assert job.get("job_id")
        assert job.get("compute_receipt", {}).get("integrity", {}).get("receipt_hash")
        print(f"OK compute job scheduled {job['job_id']} source={job.get('selected_provider', {}).get('source')}")

    mesh = req("GET", "/api/v1/compute/providers?mesh_filter=true", token=token)
    assert mesh.get("mesh_filter") is True
    print(f"OK mesh-filtered providers count={mesh.get('provider_count')}")

    lan = req("GET", "/api/v1/compute/discovery/lan")
    assert "enabled" in lan
    print(f"OK LAN discovery enabled={lan.get('enabled')}")

    if demo_contrib:
        status = (demo_contrib.get("status") or "").lower()
        if status in ("pending", "submitted", "under_review"):
            verify = req("POST", f"/api/v1/contributions/{demo_contrib['id']}/auto-verify", token=token)
            dc = verify.get("distributed_compute") or {}
            assert dc.get("witness_job", {}).get("job_id"), "auto-verify should attach witness compute schedule"
            print(f"OK auto-verify distributed_compute witness_job={dc['witness_job']['job_id'][:20]}…")
        else:
            print(f"SKIP auto-verify (contribution status={status})")

        proof = req("GET", f"/api/v1/contributions/{demo_contrib['id']}/proof")
        attr = proof.get("compute_attribution") or {}
        assert "receipt_count" in attr, "Proof packet should include compute_attribution layer (Phase β)"
        assert attr.get("spec_version") == "0.1"
        print(f"OK proof compute_attribution receipts={attr.get('receipt_count')} verified={attr.get('verified_count')}")
    else:
        print("SKIP auto-verify (no matrix demo contribution)")

    print("OK distributed compute Phase α+β+δ demo")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except urllib.error.HTTPError as exc:
        print(f"HTTP {exc.code}: {exc.read().decode()[:400]}", file=sys.stderr)
        raise SystemExit(1)
