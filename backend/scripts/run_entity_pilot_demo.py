#!/usr/bin/env python3
"""Entity Network Pilot — Epic D + metrics orchestration.

Runs (when nodes are up):
  1. Health check Node A (+ optional Node B)
  2. smoke_test on Node A (optional --skip-smoke)
  3. federation preflight + demo + strict-mode (if Node B reachable)
  4. pilot_metrics on each node

Start federation stack first:
  docker compose -f docker-compose.federation.yml up -d --build

Usage:
  python backend/scripts/run_entity_pilot_demo.py
  python backend/scripts/run_entity_pilot_demo.py --single http://127.0.0.1:8000
  python backend/scripts/run_entity_pilot_demo.py --skip-smoke
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
NODE_A_DEFAULT = "http://127.0.0.1:8100"
NODE_B_DEFAULT = "http://127.0.0.1:8101"


def _health_ok(base: str) -> bool:
    try:
        req = urllib.request.Request(f"{base.rstrip('/')}/health", method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except (urllib.error.URLError, TimeoutError):
        return False


def _run(cmd: list[str], *, label: str) -> int:
    print(f"\n=== {label} ===")
    print(" ".join(cmd))
    result = subprocess.run(cmd, cwd=BACKEND)
    if result.returncode != 0:
        print(f"FAIL: {label} (exit {result.returncode})", file=sys.stderr)
    return result.returncode


def _metrics_report(base: str) -> dict | None:
    try:
        result = subprocess.run(
            [sys.executable, "scripts/pilot_metrics.py", base, "--json"],
            cwd=BACKEND,
            capture_output=True,
            text=True,
            check=True,
        )
        return json.loads(result.stdout)
    except (subprocess.CalledProcessError, json.JSONDecodeError):
        return None


def _print_federation_summary(node_a: str, node_b: str, report_a: dict | None, report_b: dict | None) -> None:
    if not report_a or not report_b:
        return
    imports_a = report_a["protocol_layer"]["federation_imports"]
    imports_b = report_b["protocol_layer"]["federation_imports"]
    checks_a = sum(1 for v in report_a["pilot_checks"].values() if v)
    checks_b = sum(1 for v in report_b["pilot_checks"].values() if v)
    total = len(report_a["pilot_checks"])
    fed_ok = imports_a >= 1 or imports_b >= 1
    print("\n=== Federation pilot summary ===")
    print(f"  Node A ({node_a}): {checks_a}/{total} checks, federation imports={imports_a}")
    print(f"  Node B ({node_b}): {checks_b}/{total} checks, federation imports={imports_b}")
    if fed_ok:
        print("  Epic D federation_imports: OK (mirror node receives cross-node proofs)")
    else:
        print("  Epic D federation_imports: pending — run federation_demo_test.py")


def main() -> int:
    parser = argparse.ArgumentParser(description="Entity Network Pilot demo runner")
    parser.add_argument("--node-a", default=NODE_A_DEFAULT, help="Source node URL")
    parser.add_argument("--node-b", default=NODE_B_DEFAULT, help="Mirror node URL")
    parser.add_argument(
        "--single",
        metavar="URL",
        help="Single-node mode (skip federation demo)",
    )
    parser.add_argument("--skip-smoke", action="store_true", help="Skip smoke_test on Node A")
    parser.add_argument("--seed-tasks", action="store_true", help="Run seed_pilot_tasks.py first")
    args = parser.parse_args()

    node_a = args.single or args.node_a
    node_b = None if args.single else args.node_b

    if args.seed_tasks:
        node_for_seed = node_a
        code = _run(
            [sys.executable, "scripts/seed_pilot_tasks.py", "--api", node_for_seed],
            label="Seed pilot tasks via API",
        )
        if code != 0:
            return code

    if not _health_ok(node_a):
        print(f"ERROR: Node A not reachable at {node_a}", file=sys.stderr)
        print("Start: docker compose -f docker-compose.federation.yml up -d --build", file=sys.stderr)
        print("Or:    docker compose up -d --build  then  --single http://127.0.0.1:8000", file=sys.stderr)
        return 2

    print(f"OK Node A health: {node_a}")

    if not args.skip_smoke:
        code = _run(
            [sys.executable, "scripts/smoke_test.py", node_a],
            label=f"Smoke test ({node_a})",
        )
        if code != 0:
            return code

    if node_b and _health_ok(node_b):
        print(f"OK Node B health: {node_b}")
        code = _run(
            [sys.executable, "scripts/federation_pilot_preflight.py", node_a, node_b],
            label="Federation preflight (trust bundle + validate-proof)",
        )
        if code != 0:
            return code
        code = _run(
            [sys.executable, "scripts/federation_demo_test.py", node_a, node_b],
            label="Epic D federation demo",
        )
        if code != 0:
            return code
        code = _run(
            [sys.executable, "scripts/federation_strict_mode_test.py", node_a, node_b],
            label="Federation strict-mode pilot",
        )
        if code != 0:
            return code
    elif node_b:
        print(f"WARN: Node B not reachable at {node_b} — skipping federation demo")

    code = _run(
        [sys.executable, "scripts/pilot_metrics.py", node_a],
        label=f"Pilot metrics Node A ({node_a})",
    )
    if code != 0 and "--strict" in sys.argv:
        return code

    report_a = _metrics_report(node_a)
    report_b = None
    if node_b and _health_ok(node_b):
        _run(
            [sys.executable, "scripts/pilot_metrics.py", node_b],
            label=f"Pilot metrics Node B ({node_b})",
        )
        report_b = _metrics_report(node_b)
        _print_federation_summary(node_a, node_b, report_a, report_b)

    print("\n=== Entity Network Pilot demo complete ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
