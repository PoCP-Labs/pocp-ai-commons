#!/usr/bin/env python3
"""Generate ML-DSA-65 (FIPS 204) key material via liboqs-python for production hybrid nodes.

Requires: pip install liboqs-python  (+ cmake, openssl on Linux)

Usage:
  python backend/scripts/generate_liboqs_keys.py
  python backend/scripts/generate_liboqs_keys.py --mechanism ML-DSA-65

Writes hex-encoded secret/public keys for .env:
  POCP_CRYPTO_SUITE=pocp-crypto-v0.2-hybrid
  POCP_NODE_PQC_PRIVATE_KEY=...
  POCP_NODE_PQC_PUBLIC_KEY=...
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate ML-DSA keys via liboqs")
    parser.add_argument(
        "--mechanism",
        default="ML-DSA-65",
        help="liboqs signature mechanism (default ML-DSA-65)",
    )
    args = parser.parse_args()

    try:
        import oqs
    except ImportError:
        print(
            "liboqs-python not installed. Run: pip install liboqs-python",
            file=sys.stderr,
        )
        return 1

    enabled = oqs.get_enabled_sig_mechanisms()
    mechanism = args.mechanism
    if mechanism not in enabled:
        fallback = next((m for m in ("ML-DSA-65", "ML-DSA-87", "Dilithium3") if m in enabled), None)
        if fallback is None:
            print(f"No supported PQC mechanism in this liboqs build. Enabled: {enabled}", file=sys.stderr)
            return 1
        print(f"# Requested {mechanism} unavailable; using {fallback}", file=sys.stderr)
        mechanism = fallback

    with oqs.Signature(mechanism) as signer:
        public_key = signer.generate_keypair()
        secret_key = signer.export_secret_key()

    print(f"# Production PQC keys ({mechanism}) — add to .env")
    print("POCP_CRYPTO_SUITE=pocp-crypto-v0.2-hybrid")
    print("POCP_MIN_CRYPTO_SUITE=pocp-crypto-v0.2-hybrid")
    print("POCP_REQUIRE_PQC_SIGNATURE=true")
    print(f"POCP_NODE_PQC_PRIVATE_KEY={secret_key.hex()}")
    print(f"POCP_NODE_PQC_PUBLIC_KEY={public_key.hex()}")
    print(f"# mechanism={mechanism} secret_bytes={len(secret_key)} public_bytes={len(public_key)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
