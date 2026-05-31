"""Verify committed ledger anchors against a live node (distributed public memory)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.verify_standalone import audit_remote_node


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: verify_anchors.py <node_url> [anchors_dir]", file=sys.stderr)
        sys.exit(1)

    node_url = sys.argv[1]
    anchor_dir = Path(sys.argv[2] if len(sys.argv) > 2 else "anchors")

    remote = audit_remote_node(node_url)
    if not remote.get("valid"):
        print(json.dumps({"valid": False, "stage": "remote_audit", "detail": remote}, indent=2))
        sys.exit(1)

    live = remote.get("anchor") or {}
    files = sorted(anchor_dir.glob("**/ledger-anchor-*.json"))
    if not files:
        print(json.dumps({"valid": False, "error": "no anchor files"}, indent=2))
        sys.exit(1)

    latest = files[-1]
    stored = json.loads(latest.read_text(encoding="utf-8"))
    root_ok = stored.get("merkle_root") == live.get("merkle_root")
    tip_ok = stored.get("tip_hash") == live.get("tip_hash")

    result = {
        "valid": root_ok and tip_ok,
        "latest_file": str(latest),
        "stored_merkle_root": stored.get("merkle_root"),
        "live_merkle_root": live.get("merkle_root"),
        "stored_tip_hash": stored.get("tip_hash"),
        "live_tip_hash": live.get("tip_hash"),
        "node_id": live.get("node_id"),
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    sys.exit(0 if result["valid"] else 1)


if __name__ == "__main__":
    main()
