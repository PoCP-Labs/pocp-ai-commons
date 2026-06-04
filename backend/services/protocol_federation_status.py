"""Federation + cross-node protocol layer status (L1 binding over HTTPS)."""

from __future__ import annotations

import os
from typing import Any

from sqlalchemy.orm import Session

from services.compute_registry import compute_status_manifest
from services.federation_peer_addrbook import (
    addr_relay_enabled,
    auto_promote_enabled,
    bootstrap_url,
    list_addrbook_entries,
    peer_maintenance_enabled,
    promote_min_score,
    promote_min_successes,
)
from services.network.dialogue_route import peer_route_enabled
from services.protocol.schemas import federation_operator_manifest_extensions
from services.trust_config import load_trusted_nodes, trusted_nodes_source


def federation_protocol_manifest(db: Session | None = None) -> dict[str, Any]:
    """Unified federation protocol surface for operators and Agent Studio."""
    node = compute_status_manifest()
    trusted = load_trusted_nodes()
    peers_summary: dict[str, Any] = {
        "discovered_count": 0,
        "trusted_count": len(trusted),
        "routable_count": 0,
        "banned_count": 0,
        "promotion_eligible_count": 0,
    }
    if db is not None:
        entries = list_addrbook_entries(db)
        peers_summary = {
            "discovered_count": len(entries),
            "trusted_count": len(trusted),
            "routable_count": sum(1 for e in entries if e.get("routable")),
            "banned_count": sum(1 for e in entries if e.get("banned")),
            "promotion_eligible_count": sum(1 for e in entries if e.get("promotion_eligible")),
        }

    base_url = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")
    operator_ext = federation_operator_manifest_extensions(backend_url=base_url)

    return {
        "schema": "pocp.federation_protocol_manifest.v0.1",
        "spec_version": "0.1",
        "stack_layer": "L1_federation_binding",
        "stack_layer_zh": "联邦绑定层（HTTPS）",
        "principle": "Discover → probe → score → route dialogue; trust is progressive not blind.",
        "principle_zh": "发现 → 验证 → 评分 → 路由对话；信任渐进，不盲信。",
        "local_node": {
            "node_id": node.get("node_id") or os.getenv("POCP_NODE_ID"),
            "base_url": base_url,
            "node_mode": node.get("node_mode"),
        },
        "trust": {
            "source": trusted_nodes_source(),
            "trusted_peer_count": len(trusted),
            "yaml_path": "backend/config/trusted_nodes.yaml",
        },
        "peers": peers_summary,
        "features": {
            "dialogue_peer_route": peer_route_enabled(),
            "auto_discover": os.getenv("POCP_PEER_AUTO_DISCOVER", "false").lower()
            in ("1", "true", "yes", "on"),
            "addr_relay": addr_relay_enabled(),
            "peer_maintenance": peer_maintenance_enabled(),
            "auto_promote": auto_promote_enabled(),
            "bootstrap_configured": bool(bootstrap_url()),
        },
        "promotion_policy": {
            "min_successes": promote_min_successes(),
            "min_score": promote_min_score(),
        },
        "endpoints": {
            "connect": "POST /api/v1/federation/peers/connect",
            "auto_discover": "POST /api/v1/federation/peers/auto-discover",
            "addrbook": "GET /api/v1/federation/peers/addrbook",
            "maintenance": "POST /api/v1/federation/peers/maintenance",
            "promote_trust": "POST /api/v1/federation/peers/{node_id}/promote-trust",
            "network_overview": "GET /api/v1/federation/network/overview",
            "peer_manifest": "GET /api/v1/federation/peers/manifest",
            "bootstrap_example": "GET /api/v1/federation/bootstrap/example",
            "cross_node_dialogue": "POST /api/v1/federation/dialogue",
            "local_dialogue": "POST /api/v1/intelligence/dialogue",
            "import_exchange_proof": "POST /api/v1/federation/import-exchange-proof",
            "import_proof": "POST /api/v1/federation/import-proof",
            "validate_proof": "POST /api/v1/federation/validate-proof",
        },
        "discovery_sources": [
            "POCP_PEER_DISCOVERY_SEEDS",
            "POCP_PEER_BOOTSTRAP_URL",
            "manifest known_peers (addr relay)",
            "optional localhost port scan",
            "UI connect / auto-discover",
        ],
        "docs": [
            "docs/protocol/CROSS-NODE-INTERNET.md",
            "docs/protocol/ENTITY-AS-NODE-MODEL.md",
            "docs/protocol/BINDING-TO-DIALOGUE.md",
            "docs/protocol/PUBLIC-NODE-PROTOCOL.md",
            "docs/FEDERATION-DISCOVERY.md",
            "BITCOIN-INSPIRED-POCP-NETWORK.md",
        ],
        **operator_ext,
    }
