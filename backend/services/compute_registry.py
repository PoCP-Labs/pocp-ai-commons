"""Distributed compute node registry — local adapters + future peer routing."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import yaml

_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "compute_nodes.yaml"


@lru_cache(maxsize=1)
def load_compute_registry() -> dict:
    if not _CONFIG_PATH.exists():
        return {"spec_version": "0.1", "registry": "compute_nodes", "local_node": {}, "peer_compute": {}}
    with _CONFIG_PATH.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _adapter_live(item: dict) -> bool:
    env_key = item.get("env")
    if env_key:
        val = os.getenv(str(env_key), "")
        if env_key.endswith("_VERIFIER") or env_key.startswith("ENABLE_"):
            return val.lower() in ("true", "1", "yes", "on")
        return bool(val.strip())
    return item.get("status") == "active"


def compute_status_manifest() -> dict:
    """Runtime view of which compute adapters are active on this node."""
    from services.peer_compute import list_peer_compute_status, peer_compute_enabled

    registry = load_compute_registry()
    local = registry.get("local_node") or {}
    adapters = local.get("adapters") or []
    active = [a["name"] for a in adapters if isinstance(a, dict) and _adapter_live(a)]
    peer_status = list_peer_compute_status() if peer_compute_enabled() else None
    return {
        "spec_version": registry.get("spec_version", "0.1"),
        "node_id": os.getenv("POCP_NODE_ID", local.get("node_id") or "unknown"),
        "roles": local.get("roles") or [],
        "active_adapters": active,
        "adapters": [
            {
                "name": a.get("name"),
                "kind": a.get("kind"),
                "status": "active" if _adapter_live(a) else "inactive",
            }
            for a in adapters
            if isinstance(a, dict)
        ],
        "peer_compute_enabled": peer_compute_enabled(),
        "peer_mcp_enabled": _peer_mcp_enabled_label(),
        "peer_compute": peer_status,
        "routing_policy": registry.get("routing_policy") or {},
        "embedding_provider": _embedding_provider_label(),
        "witness_endpoint": "/api/v1/intelligence/compute/witness",
        "mcp_invoke_endpoint": "/api/v1/intelligence/compute/mcp/invoke",
    }


def _peer_mcp_enabled_label() -> bool:
    from services.peer_mcp import peer_mcp_enabled

    return peer_mcp_enabled()


def _embedding_provider_label() -> str | None:
    from services.embedding_match import embedding_provider

    return embedding_provider()
