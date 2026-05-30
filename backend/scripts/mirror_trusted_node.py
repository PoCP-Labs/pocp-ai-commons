"""Pull approved contribution proofs from a trusted peer node."""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.federation_sync import sync_peers_http


def main() -> None:
    if len(sys.argv) >= 3:
        source_url = sys.argv[1]
        source_node_id = sys.argv[2]
        target_url = sys.argv[3] if len(sys.argv) > 3 else os.getenv("POCP_MIRROR_TARGET", "http://127.0.0.1:8000")
        os.environ["POCP_MIRROR_SOURCES"] = json.dumps(
            [{"base_url": source_url, "node_id": source_node_id}]
        )
        os.environ["POCP_MIRROR_TARGET"] = target_url

    summary = sync_peers_http()
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    errors = sum(1 for r in summary.get("results", []) if r.get("status") == "error")
    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
