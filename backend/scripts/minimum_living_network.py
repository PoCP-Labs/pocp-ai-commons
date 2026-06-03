from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.cip.examples.minimum_living_network import run_minimum_living_network_demo


def main() -> int:
    result = run_minimum_living_network_demo()
    required = [
        "skill_node",
        "capability",
        "invocation",
        "proof",
        "verification",
        "settlement",
        "accounts",
        "skill_reputation",
        "events",
    ]
    missing = [key for key in required if key not in result]
    if missing:
        print(f"[FAIL] Missing result keys: {missing}")
        return 1
    print("[OK] minimum_living_network passed.")
    print(f"Invocation: {result['invocation'].invocation_id}")
    print(f"Settlement: {result['settlement'].settlement_id}")
    print(f"Events: {len(result['events'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
