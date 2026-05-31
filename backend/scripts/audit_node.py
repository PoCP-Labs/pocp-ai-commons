#!/usr/bin/env python3
"""PoCP audit node CLI — verify ledger and proofs without trusting the operator.

Bitcoin-inspired: like running bitcoind getblockchaininfo, but for contribution history.

Usage:
  python scripts/audit_node.py remote --url http://127.0.0.1:8000
  python scripts/audit_node.py ledger --file ledger_export.json
  python scripts/audit_node.py wallets --file wallets_export.json
  python scripts/audit_node.py proof --file contribution_proof.json
  python scripts/audit_node.py anchors --dir ../anchors --url http://127.0.0.1:8000
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.ledger_merkle import verify_merkle_inclusion
from services.verify_standalone import audit_remote_node, verify_ledger_export, verify_proof_integrity
from services.wallet_audit import verify_wallet_export


def _load_json(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _print_result(result: dict) -> int:
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    return 0 if result.get("valid") else 1


def cmd_remote(args: argparse.Namespace) -> int:
    return _print_result(audit_remote_node(args.url))


def cmd_ledger(args: argparse.Namespace) -> int:
    export = _load_json(args.file)
    return _print_result(verify_ledger_export(export))


def cmd_wallets(args: argparse.Namespace) -> int:
    export = _load_json(args.file)
    return _print_result(verify_wallet_export(export))


def cmd_proof(args: argparse.Namespace) -> int:
    proof = _load_json(args.file)
    result = verify_proof_integrity(
        proof,
        trusted_public_key=args.public_key,
        require_signature=args.require_signature,
    )
    return _print_result(result)


def cmd_anchors(args: argparse.Namespace) -> int:
    """Compare committed anchor files against a live node's current anchor."""
    remote = audit_remote_node(args.url)
    live_root = (remote.get("anchor") or {}).get("merkle_root")
    live_tip = (remote.get("anchor") or {}).get("tip_hash")
    anchor_dir = Path(args.dir)
    files = sorted(anchor_dir.glob("**/ledger-anchor-*.json"))
    if not files:
        print(json.dumps({"valid": False, "error": f"No anchor files under {anchor_dir}"}, indent=2))
        return 1

    comparisons = []
    all_valid = remote.get("valid", False)
    for path in files[-5:]:
        stored = _load_json(str(path))
        root_match = stored.get("merkle_root") == live_root
        tip_match = stored.get("tip_hash") == live_tip
        comparisons.append(
            {
                "file": str(path),
                "stored_merkle_root": stored.get("merkle_root"),
                "live_merkle_root": live_root,
                "merkle_root_matches_live": root_match,
                "tip_hash_matches_live": tip_match,
                "stored_date": path.stem.replace("ledger-anchor-", ""),
            }
        )
        if path == files[-1] and not root_match:
            all_valid = False

    result = {
        "valid": all_valid,
        "remote_audit": remote.get("valid"),
        "live_merkle_root": live_root,
        "live_tip_hash": live_tip,
        "compared_files": comparisons,
        "note": "Latest anchor should match live node unless chain grew since commit.",
    }
    return _print_result(result)


def cmd_merkle(args: argparse.Namespace) -> int:
    bundle = _load_json(args.file)
    valid = verify_merkle_inclusion(
        bundle.get("leaf_hash") or "",
        bundle.get("merkle_proof") or [],
        bundle.get("merkle_root") or "",
    )
    return _print_result({**bundle, "valid": valid})


def main() -> None:
    parser = argparse.ArgumentParser(description="PoCP standalone audit node (verify, don't trust)")
    sub = parser.add_subparsers(dest="command", required=True)

    remote = sub.add_parser("remote", help="Full audit of a live PoCP node")
    remote.add_argument("--url", required=True, help="Node base URL")
    remote.set_defaults(func=cmd_remote)

    ledger = sub.add_parser("ledger", help="Verify an exported ledger JSON file")
    ledger.add_argument("--file", required=True, help="Path to ledger export JSON")
    ledger.set_defaults(func=cmd_ledger)

    wallets = sub.add_parser("wallets", help="Verify wallet balances from export JSON")
    wallets.add_argument("--file", required=True, help="Path to wallets export JSON")
    wallets.set_defaults(func=cmd_wallets)

    proof = sub.add_parser("proof", help="Verify an exported contribution proof JSON file")
    proof.add_argument("--file", required=True, help="Path to proof JSON")
    proof.add_argument("--public-key", default=None, help="Trusted node Ed25519 public key (hex)")
    proof.add_argument(
        "--require-signature",
        action="store_true",
        help="Fail if proof lacks federation signature",
    )
    proof.set_defaults(func=cmd_proof)

    anchors = sub.add_parser("anchors", help="Compare repo anchors vs live node")
    anchors.add_argument("--dir", default="../anchors", help="Anchors directory")
    anchors.add_argument("--url", required=True, help="Live node base URL")
    anchors.set_defaults(func=cmd_anchors)

    merkle = sub.add_parser("merkle", help="Verify a Merkle inclusion proof bundle")
    merkle.add_argument("--file", required=True, help="Path to merkle proof JSON")
    merkle.set_defaults(func=cmd_merkle)

    args = parser.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
