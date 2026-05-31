"""Fetch ledger anchor from a remote PoCP node (for CI without database access)."""

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


def fetch_anchor(node_url: str) -> dict:
    url = f"{node_url.rstrip('/')}/api/v1/ledger/anchor"
    with urllib.request.urlopen(url, timeout=60) as response:
        return json.loads(response.read().decode())


def write_anchor(anchor: dict, out_dir: Path) -> Path:
    node_id = anchor.get("node_id", "unknown")
    node_dir = out_dir / node_id
    node_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    out_path = node_dir / f"ledger-anchor-{stamp}.json"
    out_path.write_text(json.dumps(anchor, indent=2, ensure_ascii=False), encoding="utf-8")
    return out_path


def main() -> None:
    node_url = sys.argv[1] if len(sys.argv) > 1 else os.getenv("POCP_ANCHOR_NODE_URL", "")
    out_dir = Path(sys.argv[2] if len(sys.argv) > 2 else "anchors")
    if not node_url:
        print("Usage: fetch_anchor.py <node_url> [out_dir]", file=sys.stderr)
        print("Or set POCP_ANCHOR_NODE_URL", file=sys.stderr)
        sys.exit(1)

    try:
        anchor = fetch_anchor(node_url)
    except urllib.error.HTTPError as exc:
        print(f"HTTP {exc.code}: {exc.read().decode()}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as exc:
        print(f"Request failed: {exc.reason}", file=sys.stderr)
        sys.exit(1)

    if os.getenv("POCP_ANCHOR_VERIFY_REMOTE", "true").lower() == "true":
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        from services.verify_standalone import audit_remote_node

        audit = audit_remote_node(node_url)
        if not audit.get("valid"):
            print(json.dumps({"error": "remote node failed audit", "audit": audit}, indent=2), file=sys.stderr)
            sys.exit(1)
        print(f"Remote audit OK: tip={audit.get('verify', {}).get('tip_hash', '')[:16]}…", file=sys.stderr)

    out_path = write_anchor(anchor, out_dir)
    print(json.dumps(anchor, indent=2, ensure_ascii=False))
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
