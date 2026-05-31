#!/usr/bin/env python3
"""Smoke test: federated peer witness routing (NN-5).

Requires federation stack with ENABLE_PEER_COMPUTE on source node:
  docker compose -f docker-compose.federation.yml up -d

Usage:
  python backend/scripts/peer_compute_demo_test.py
  python backend/scripts/peer_compute_demo_test.py http://127.0.0.1:8100
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

DEFAULT_BASE = "http://127.0.0.1:8100"


def get_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=15) as resp:
        return json.loads(resp.read().decode())


def post_json(url: str, body: dict) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def main(base: str) -> int:
    root = base.rstrip("/")
    print(f"Peer compute demo against {root}")

    status = get_json(f"{root}/api/v1/intelligence/compute/status")
    print("compute/status:", json.dumps(status, indent=2)[:800])

    peers = get_json(f"{root}/api/v1/intelligence/compute/peers")
    print("compute/peers reachable:", peers.get("reachable_count"), "/", peers.get("peer_count"))

    witness = post_json(
        f"{root}/api/v1/intelligence/compute/witness",
        {
            "context": {
                "task": {"title": "Peer witness smoke test"},
                "contribution": {"description": "Testing federated compute endpoint"},
                "participants": [],
            },
            "provider": "mock",
        },
    )
    assert "result" in witness, witness
    assert witness["result"].get("quality") is not None
    print("local witness OK — quality:", witness["result"].get("quality"))

    if not status.get("peer_compute_enabled"):
        print("NOTE: ENABLE_PEER_COMPUTE not set on this node — peer verifiers inactive until enabled.")
        return 0

    if peers.get("reachable_count", 0) == 0:
        print("WARN: no reachable peer compute nodes")
        return 1

    print("PASS: peer compute layer reachable")
    return 0


if __name__ == "__main__":
    base_url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_BASE
    try:
        raise SystemExit(main(base_url))
    except urllib.error.HTTPError as exc:
        print(f"HTTP {exc.code}: {exc.read().decode()}", file=sys.stderr)
        raise SystemExit(1)
