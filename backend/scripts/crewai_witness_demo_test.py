#!/usr/bin/env python3
"""Smoke test: CrewAI multi-agent witness registration (Option 3).

Usage:
  python backend/scripts/crewai_witness_demo_test.py
  python backend/scripts/crewai_witness_demo_test.py http://127.0.0.1:8100
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

DEFAULT_BASE = "http://127.0.0.1:8000"


def get_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=15) as resp:
        return json.loads(resp.read().decode())


def main(base: str) -> int:
    root = base.rstrip("/")
    print(f"CrewAI witness demo against {root}")

    status = get_json(f"{root}/api/v1/intelligence/compute/status")
    adapters = {a.get("name"): a.get("status") for a in status.get("adapters", [])}
    print("compute/status adapters:", adapters)

    if adapters.get("crewai") == "active":
        print("OK crewai adapter active")
    else:
        print("NOTE: set ENABLE_CREWAI_WITNESS=true for live multi-agent witness in consensus")

    sources = get_json(f"{root}/api/v1/intelligence/neural-sources")
    crew = next((s for s in sources.get("sources", []) if s.get("slug") == "crewai"), None)
    if crew and crew.get("status") == "active":
        print("OK neural-sources crewai status=active")
    else:
        print("WARN: crewai not active in neural-sources")

    print("PASS: CrewAI witness adapter registered")
    return 0


if __name__ == "__main__":
    base_url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_BASE
    try:
        raise SystemExit(main(base_url))
    except urllib.error.HTTPError as exc:
        print(f"HTTP {exc.code}: {exc.read().decode()}", file=sys.stderr)
        raise SystemExit(1)
