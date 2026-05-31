#!/usr/bin/env python3
"""Phase A acceptance — orchestrate Sprint Alpha + federation E2E scripts.

Usage:
  python backend/scripts/run_phase_a_acceptance.py [base_url]
  python backend/scripts/run_phase_a_acceptance.py http://127.0.0.1:8100 --federation http://127.0.0.1:8101

Exit 0 when all required steps pass; 1 on failure.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
DEFAULT_BASE = "http://127.0.0.1:8000"


def get_json(url: str, timeout: float = 15) -> dict:
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def run_script(name: str, base: str, extra_args: list[str] | None = None) -> tuple[bool, str]:
    path = SCRIPTS / name
    cmd = [sys.executable, str(path), base, *(extra_args or [])]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    out = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode == 0, out.strip()


def step_health(base: str) -> tuple[bool, str]:
    try:
        data = get_json(f"{base.rstrip('/')}/health")
        ok = data.get("status") == "ok"
        return ok, json.dumps(data)
    except Exception as exc:
        return False, str(exc)


def step_crypto_readiness(base: str, *, require_hybrid: bool = False) -> tuple[bool, str]:
    try:
        data = get_json(f"{base.rstrip('/')}/api/v1/crypto/readiness")
        if require_hybrid:
            ok = (
                data.get("active_crypto_suite") == "pocp-crypto-v0.2-hybrid"
                and data.get("hybrid_signing_enabled") is True
            )
        else:
            ok = bool(data.get("active_crypto_suite"))
        return ok, json.dumps(
            {
                "suite": data.get("active_crypto_suite"),
                "hybrid": data.get("hybrid_signing_enabled"),
                "hash": data.get("active_hash_algorithm"),
            }
        )
    except Exception as exc:
        return False, str(exc)


def step_intelligence_status(base: str) -> tuple[bool, str]:
    try:
        data = get_json(f"{base.rstrip('/')}/api/v1/intelligence/status")
        modules = data.get("modules") or []
        return len(modules) >= 5, f"modules={len(modules)} active={data.get('modules_active')}"
    except Exception as exc:
        return False, str(exc)


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase A acceptance runner")
    parser.add_argument("base", nargs="?", default=DEFAULT_BASE, help="API base URL")
    parser.add_argument(
        "--federation",
        metavar="NODE_B_URL",
        default=None,
        help="If set, run federation E2E against node A (base) and optional node B URL",
    )
    parser.add_argument("--skip-optional", action="store_true", help="Skip optional demo scripts")
    args = parser.parse_args()

    base = args.base.rstrip("/")
    federation = args.federation is not None
    node_b = (args.federation or "http://127.0.0.1:8101").rstrip("/")

    print(f"Phase A acceptance @ {base}" + (f" (federation, peer={node_b})" if federation else ""))
    failures: list[str] = []

    checks: list[tuple[str, callable]] = [
        ("health", lambda: step_health(base)),
        ("intelligence/status", lambda: step_intelligence_status(base)),
        ("smoke_test", lambda: run_script("smoke_test.py", base)),
    ]

    if federation:
        checks.extend(
            [
                ("crypto_readiness", lambda: step_crypto_readiness(base)),
                ("crypto_readiness_peer", lambda: step_crypto_readiness(node_b)),
                ("federation_demo", lambda: run_script("federation_demo_test.py", base, [node_b])),
                ("peer_witness_verify", lambda: run_script("peer_witness_verify_test.py", base)),
                ("peer_mcp_demo", lambda: run_script("peer_mcp_demo_test.py", base)),
            ]
        )
    else:        checks.append(("mcp_import_demo", lambda: run_script("mcp_import_demo_test.py", base)))

    if not args.skip_optional:
        checks.extend(
            [
                ("crewai_witness_demo", lambda: run_script("crewai_witness_demo_test.py", base)),
                ("crewai_witness_e2e", lambda: run_script("crewai_witness_e2e_test.py", base)),
            ]
        )

    for name, fn in checks:
        try:
            ok, detail = fn()
        except subprocess.TimeoutExpired:
            ok, detail = False, "timeout"
        except urllib.error.URLError as exc:
            ok, detail = False, str(exc.reason)

        status = "OK" if ok else "FAIL"
        print(f"  [{status}] {name}")
        if detail and (not ok or len(detail) < 200):
            for line in detail.splitlines()[:8]:
                print(f"         {line}")
        elif detail and not ok:
            print(f"         {detail[:400]}…")

        if not ok and name in (
            "health",
            "intelligence/status",
            "crypto_readiness",
            "crypto_readiness_peer",
            "smoke_test",
            "federation_demo",
            "peer_witness_verify",
            "peer_mcp_demo",
        ):
            failures.append(name)

    if failures:
        print(f"\nPhase A FAILED — required steps: {', '.join(failures)}")
        return 1

    print("\nPhase A PASS — demonstrable loop verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
