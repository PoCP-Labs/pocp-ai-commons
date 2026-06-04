"""Federation protocol operator manifest — frozen contract (CIP-P0.2).

Schema: ``pocp.federation_protocol_manifest.v0.1``
Wire: ``GET /api/v1/intelligence/protocol/federation``
"""

from __future__ import annotations

import os
from typing import Any

from sqlalchemy.orm import Session

from services.federation_peer_addrbook import (
    addr_relay_enabled,
    auto_promote_enabled,
    bootstrap_url,
    list_addrbook_entries,
    promote_min_score,
    promote_min_successes,
    promote_trust_weight,
)
from services.node.schemas import (
    FEDERATION_PROTOCOL_MANIFEST_SCHEMA,
    OPERATOR_MANIFEST_EXCHANGE_IMPORT_KEYS,
    OPERATOR_MANIFEST_REQUIRED_ENDPOINT_KEYS,
    build_operator_protocol_endpoints,
)
from services.trust_config import load_trusted_nodes


def _env_flag(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).lower() in ("1", "true", "yes", "on")


def _backend_url() -> str:
    return os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")


def _node_id() -> str:
    return os.getenv("POCP_NODE_ID", "pocp-node-local")


def _addrbook_summary(db: Session) -> dict[str, Any]:
    entries = list_addrbook_entries(db)
    discovered = sum(1 for e in entries if e.get("discovered"))
    banned = sum(1 for e in entries if e.get("banned"))
    routable = sum(1 for e in entries if e.get("routable"))
    promotion_eligible = sum(1 for e in entries if e.get("promotion_eligible"))
    return {
        "discovered_peer_count": discovered,
        "addrbook_entry_count": len(entries),
        "banned_count": banned,
        "routable_count": routable,
        "promotion_eligible_count": promotion_eligible,
    }


def federation_protocol_manifest(db: Session) -> dict[str, Any]:
    """Operator manifest: addrbook, feature flags, promotion policy, stable endpoint map."""
    backend = _backend_url()
    trusted = load_trusted_nodes()
    return {
        "schema": FEDERATION_PROTOCOL_MANIFEST_SCHEMA,
        "spec_version": "0.1",
        "node_id": _node_id(),
        "base_url": backend,
        "operator_surface": True,
        "addrbook": _addrbook_summary(db),
        "trusted_peer_count": len(trusted),
        "feature_flags": {
            "dialogue_peer_route": _env_flag("POCP_DIALOGUE_PEER_ROUTE"),
            "peer_auto_discover": _env_flag("POCP_PEER_AUTO_DISCOVER"),
            "peer_addr_relay": addr_relay_enabled(),
            "peer_auto_promote": auto_promote_enabled(),
            "peer_maintenance": _env_flag("POCP_PEER_MAINTENANCE", "true"),
        },
        "promotion_policy": {
            "min_successes": promote_min_successes(),
            "min_score": promote_min_score(),
            "trust_weight": promote_trust_weight(),
            "bootstrap_url": bootstrap_url() or None,
        },
        "endpoints": build_operator_protocol_endpoints(backend_url=backend),
        "exchange_import": {
            "import_exchange_proof": f"{backend}/api/v1/federation/import-exchange-proof",
            "import_proof": f"{backend}/api/v1/federation/import-proof",
            "validate_proof": f"{backend}/api/v1/federation/validate-proof",
            "exchange_kind": "capability | compute | hybrid",
            "acceptance_levels": ["L0", "L1", "L2", "L3"],
        },
        "cross_node": {
            "peer_connect": f"{backend}/api/v1/federation/peers/connect",
            "peer_handshake": f"{backend}/api/v1/federation/peers/handshake",
            "peer_dialogue": f"{backend}/api/v1/federation/dialogue",
            "overlay_relay": f"{backend}/api/v1/federation/overlay/relay",
        },
        "docs": {
            "federation_discovery": "docs/FEDERATION-DISCOVERY.md",
            "cross_node": "docs/protocol/CROSS-NODE-INTERNET.md",
            "binding_map": "docs/protocol/BINDING-TO-DIALOGUE.md",
            "public_node": "docs/protocol/PUBLIC-NODE-PROTOCOL.md",
            "exchange_spine": "docs/protocol/EXCHANGE-SPINE-v0.1.md",
        },
    }


def validate_federation_protocol_manifest(manifest: dict[str, Any]) -> None:
    """Raise ValueError when operator manifest violates frozen contract."""
    if manifest.get("schema") != FEDERATION_PROTOCOL_MANIFEST_SCHEMA:
        raise ValueError(f"Unexpected schema: {manifest.get('schema')!r}")
    endpoints = manifest.get("endpoints") or {}
    missing = sorted(key for key in OPERATOR_MANIFEST_REQUIRED_ENDPOINT_KEYS if key not in endpoints)
    if missing:
        raise ValueError(f"Operator endpoints missing keys: {missing}")
    exchange_import = manifest.get("exchange_import") or {}
    missing_import = sorted(
        key for key in OPERATOR_MANIFEST_EXCHANGE_IMPORT_KEYS if key not in exchange_import
    )
    if missing_import:
        raise ValueError(f"exchange_import missing keys: {missing_import}")
