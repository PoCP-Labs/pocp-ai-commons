#!/usr/bin/env python3
"""Public node preflight for HTTPS-deployed PoCP operators.

Usage:
  python backend/scripts/public_node_preflight.py https://api.node-a.example.com
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from urllib.parse import urlparse


def _get_json(url: str, timeout: float = 30.0) -> dict | list:
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode())


def _normalize_base_url(raw: str) -> str:
    base = raw.rstrip("/")
    parsed = urlparse(base)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError("Base URL must include http(s) scheme and host")
    return base


def run_preflight(base_url: str) -> dict:
    base = _normalize_base_url(base_url)

    health = _get_json(f"{base}/health")
    node = _get_json(f"{base}/api/v1/federation/node")
    manifest = _get_json(f"{base}/.well-known/pocp-node.json")
    trust = _get_json(f"{base}/api/v1/federation/trust")
    peers = _get_json(f"{base}/api/v1/federation/peers/health")
    ledger = _get_json(f"{base}/api/v1/ledger/verify")
    anchor = _get_json(f"{base}/api/v1/ledger/anchor?skip_cosign=true")

    issues: list[str] = []

    if health.get("service") != "pocp-ai-commons":
        issues.append(f"Unexpected service name: {health.get('service')}")
    if health.get("status") not in ("ok", "degraded"):
        issues.append(f"Unexpected health status: {health.get('status')}")

    if manifest.get("kind") != "instance":
        issues.append("Well-known node manifest is not an instance manifest")
    if not manifest.get("instance_id"):
        issues.append("Well-known node manifest missing instance_id")

    if not node.get("node_id"):
        issues.append("Federation node endpoint missing node_id")
    if not node.get("public_key"):
        issues.append("Federation node endpoint missing public_key")

    trusted_nodes = trust.get("trusted_nodes") or []
    unreachable = [
        p.get("node_id")
        for p in (peers.get("peers") or [])
        if not p.get("reachable")
    ]

    if trusted_nodes and unreachable:
        issues.append(f"Trusted peers unreachable: {', '.join(unreachable)}")

    if ledger.get("valid") is not True:
        issues.append("Ledger verify endpoint is not valid")
    if not anchor.get("merkle_root"):
        issues.append("Ledger anchor missing merkle_root")

    return {
        "valid": not issues,
        "base_url": base,
        "node_id": node.get("node_id"),
        "instance_id": manifest.get("instance_id"),
        "node_mode": node.get("node_mode"),
        "trusted_peer_count": len(trusted_nodes),
        "reachable_peer_count": len(trusted_nodes) - len(unreachable),
        "health": {
            "status": health.get("status"),
            "version": health.get("version"),
            "stage": health.get("stage"),
            "crypto_suite": health.get("crypto_suite"),
        },
        "ledger": {
            "valid": ledger.get("valid"),
            "count": ledger.get("count"),
            "tip_hash": anchor.get("tip_hash"),
            "merkle_root": anchor.get("merkle_root"),
        },
        "issues": issues,
    }


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python backend/scripts/public_node_preflight.py https://api.node-a.example.com", file=sys.stderr)
        return 1

    result = run_preflight(sys.argv[1])
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result.get("valid") else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode()
        print(json.dumps({"valid": False, "error": f"HTTP {exc.code}", "body": body}, indent=2), file=sys.stderr)
        raise SystemExit(1)
    except urllib.error.URLError as exc:
        print(json.dumps({"valid": False, "error": str(exc.reason)}, indent=2), file=sys.stderr)
        raise SystemExit(1)
    except ValueError as exc:
        print(json.dumps({"valid": False, "error": str(exc)}, indent=2), file=sys.stderr)
        raise SystemExit(1)
