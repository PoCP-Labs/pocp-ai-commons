"""Mirror contribution proofs from POCP_MIRROR_SOURCES into POCP_MIRROR_TARGET (HTTP mode)."""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.federation_sync import sync_peers_http


def main() -> None:
    raw = os.getenv("POCP_MIRROR_SOURCES", "[]")
    if not json.loads(raw or "[]"):
        print("POCP_MIRROR_SOURCES is empty; nothing to mirror.", file=sys.stderr)
        sys.exit(0)

    summary = sync_peers_http()
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    errors = sum(1 for r in summary.get("results", []) if r.get("status") == "error")
    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
