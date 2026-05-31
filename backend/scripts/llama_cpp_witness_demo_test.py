#!/usr/bin/env python3
"""Smoke test: llama.cpp witness adapter registration (Option 1).

Requires backend running; live witness needs llama-server with OpenAI API:
  llama-server -m /path/to/model.gguf --port 8080

Usage:
  python backend/scripts/llama_cpp_witness_demo_test.py
  python backend/scripts/llama_cpp_witness_demo_test.py http://127.0.0.1:8100
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
    print(f"llama.cpp witness demo against {root}")

    status = get_json(f"{root}/api/v1/intelligence/compute/status")
    adapters = {a.get("name"): a.get("status") for a in status.get("adapters", [])}
    print("compute/status adapters:", adapters)

    if "llama_cpp" not in adapters:
        print("WARN: llama_cpp adapter missing from compute_nodes.yaml registry")
        return 1

    if adapters.get("llama_cpp") == "active":
        print("OK llama_cpp adapter active (ENABLE_LLAMA_CPP_VERIFIER=true)")
    else:
        print("NOTE: llama_cpp inactive — set ENABLE_LLAMA_CPP_VERIFIER=true and run llama-server")

    sources = get_json(f"{root}/api/v1/intelligence/neural-sources")
    llama = next(
        (s for s in sources.get("sources", []) if s.get("slug") == "llama_cpp"),
        None,
    )
    if llama and llama.get("status") == "active":
        print("OK neural-sources llama_cpp status=active")
    else:
        print("WARN: neural-sources missing active llama_cpp entry")

    print("PASS: llama.cpp witness adapter registered")
    return 0


if __name__ == "__main__":
    base_url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_BASE
    try:
        raise SystemExit(main(base_url))
    except urllib.error.HTTPError as exc:
        print(f"HTTP {exc.code}: {exc.read().decode()}", file=sys.stderr)
        raise SystemExit(1)
