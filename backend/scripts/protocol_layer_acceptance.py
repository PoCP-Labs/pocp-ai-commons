#!/usr/bin/env python3
"""PL-9 / PN-6 protocol layer acceptance gate — pytest + network smoke."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_BACKEND = _REPO / "backend"


def main() -> int:
    print("=== Protocol layer acceptance (PL-9 / PN-6) ===\n")
    tests = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/test_entity_dialogue.py",
            "tests/test_entity_connections.py",
            "tests/test_trust_policy_bundle.py",
            "tests/test_federation_overlay.py",
            "tests/test_protocol_network.py",
            "tests/test_merkle_canonical.py",
            "tests/test_overlay_persistence.py",
            "tests/test_overlay_gossip.py",
            "-q",
        ],
        cwd=_BACKEND,
    )
    smoke = subprocess.run(
        [sys.executable, str(_BACKEND / "scripts/bitcoin_inspired_network_smoke.py")],
        cwd=_REPO,
    )
    if tests.returncode == 0 and smoke.returncode == 0:
        print("\n[PASS] Protocol layer acceptance gate green.")
        print("Next: Agent Studio PL-10 — Nexus consolidate protocol_layer_edp / protocol_native_stack missions.")
        return 0
    print("\n[FAIL] Fix failing tests or smoke before PL-10 closeout.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
