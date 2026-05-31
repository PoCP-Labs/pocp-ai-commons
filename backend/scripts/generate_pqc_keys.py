#!/usr/bin/env python3
"""Generate PQC key material for hybrid crypto suite testing or production.

Modes:
  stub (default) — 32-byte dev stub for wire-format / federation demo (no liboqs)
  liboqs         — ML-DSA-65 production keys (requires liboqs-python)

Usage:
  python backend/scripts/generate_pqc_keys.py
  python backend/scripts/generate_pqc_keys.py --mode liboqs
"""

from __future__ import annotations

import argparse
import hashlib
import secrets
import subprocess
import sys
from pathlib import Path


def _stub_keys() -> int:
    private = secrets.token_bytes(32)
    public = hashlib.sha256(private).hexdigest()
    print("# Dev stub keys (ml-dsa-dev-stub-v0) — federation demo / CI")
    print("POCP_CRYPTO_SUITE=pocp-crypto-v0.2-hybrid")
    print(f"POCP_NODE_PQC_PRIVATE_KEY={private.hex()}")
    print(f"POCP_NODE_PQC_PUBLIC_KEY={public}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate PQC keys for PoCP hybrid suite")
    parser.add_argument(
        "--mode",
        choices=("stub", "liboqs"),
        default="stub",
        help="stub=dev HMAC stub; liboqs=ML-DSA-65 production keys",
    )
    args = parser.parse_args()

    if args.mode == "liboqs":
        script = Path(__file__).resolve().parent / "generate_liboqs_keys.py"
        return subprocess.call([sys.executable, str(script)])

    return _stub_keys()


if __name__ == "__main__":
    raise SystemExit(main())
