from __future__ import annotations

import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_BACKEND))

from services.network.examples.bitcoin_inspired_network_demo import (  # noqa: E402
    run_bitcoin_inspired_network_demo,
)

def main() -> int:
    result = run_bitcoin_inspired_network_demo()
    required = ["peers", "events", "batch", "merkle_root", "confirmation"]
    missing = [key for key in required if key not in result]
    if missing:
        print(f"[FAIL] Missing keys: {missing}")
        return 1

    print("[OK] Bitcoin-inspired PoCP network smoke passed.")
    print(f"Peers: {len(result['peers'])}")
    print(f"Events: {len(result['events'])}")
    print(f"Batch: {result['batch'].batch_id}")
    print(f"Merkle root: {result['merkle_root']}")
    print(f"Confirmation: {result['confirmation'].level} - {result['confirmation'].label}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
