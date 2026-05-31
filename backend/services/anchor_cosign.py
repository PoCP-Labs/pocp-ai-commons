"""Multi-operator Merkle anchor attestations — Bitcoin-style distributed public memory.

When trusted peers report the same merkle_root + tip_hash, their signatures are
bundled as peer attestations so third parties need not trust a single operator.

Peer fetches use `GET /api/v1/ledger/anchor?skip_cosign=true` to avoid recursive
cross-node deadlocks during federation health checks and cosign collection.
"""

from __future__ import annotations

import os
import urllib.error
import urllib.request
from typing import Any

from services.federation_crypto import verify_message
from services.federation_peers import _get_json
from services.trust_config import load_trusted_nodes


def anchor_cosign_enabled() -> bool:
    env = os.getenv("ENABLE_ANCHOR_COSIGN", "true").strip().lower()
    return env not in ("false", "0", "no", "off")


def collect_peer_anchor_attestations(
    merkle_root: str,
    tip_hash: str | None,
    graph_merkle_root: str | None = None,
    *,
    timeout: float = 10.0,
) -> list[dict[str, Any]]:
    """Fetch trusted peers' anchors; include signatures when root+tip match local."""
    if not anchor_cosign_enabled() or not merkle_root:
        return []

    local_node_id = os.getenv("POCP_NODE_ID", "unknown")
    attestations: list[dict[str, Any]] = []

    for node in load_trusted_nodes():
        if node.node_id == local_node_id:
            continue
        base = (node.base_url or "").rstrip("/")
        if not base or not node.public_key:
            continue
        try:
            anchor = _get_json(f"{base}/api/v1/ledger/anchor?skip_cosign=true", timeout=timeout)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError):
            continue

        if anchor.get("merkle_root") != merkle_root:
            continue
        if graph_merkle_root and anchor.get("graph_merkle_root") != graph_merkle_root:
            continue
        if tip_hash and anchor.get("tip_hash") and anchor.get("tip_hash") != tip_hash:
            continue
        if not anchor.get("ledger_valid"):
            continue

        federation = anchor.get("federation") or {}
        signatures = federation.get("signatures") or {}
        classic = signatures.get("classic") or {}
        signature = federation.get("signature") or classic.get("signature")
        public_key = federation.get("public_key") or node.public_key

        if not signature or not public_key:
            continue
        if not verify_message(merkle_root, signature, public_key):
            continue

        attestations.append(
            {
                "node_id": node.node_id,
                "base_url": base,
                "merkle_root": merkle_root,
                "tip_hash": anchor.get("tip_hash"),
                "public_key": public_key,
                "signature": signature,
                "signed_field": federation.get("signed_field") or "merkle_root",
                "trust_weight": float(node.trust_weight),
            }
        )

    return attestations


def verify_anchor_attestations(anchor: dict[str, Any]) -> dict[str, Any]:
    """Verify bundled peer attestations on an anchor object."""
    root = anchor.get("merkle_root") or ""
    attestations = anchor.get("peer_attestations") or []
    results = []
    valid_count = 0
    for item in attestations:
        sig = item.get("signature")
        pk = item.get("public_key")
        item_root = item.get("merkle_root") or root
        ok = bool(sig and pk and verify_message(item_root, sig, pk))
        if ok:
            valid_count += 1
        results.append(
            {
                "node_id": item.get("node_id"),
                "valid": ok,
                "merkle_root_matches": item_root == root,
            }
        )
    return {
        "valid": valid_count == len(attestations) if attestations else True,
        "attestation_count": len(attestations),
        "valid_count": valid_count,
        "checks": results,
    }
