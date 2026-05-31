"""NN-5 — Federated inference routing across trusted peer compute nodes."""

from __future__ import annotations

import itertools
import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from services.compute_registry import load_compute_registry
from services.trust_config import load_trusted_nodes

WITNESS_PATH = "/api/v1/intelligence/compute/witness"
MCP_INVOKE_PATH = "/api/v1/intelligence/compute/mcp/invoke"
_round_robin = itertools.count()


@dataclass(frozen=True)
class PeerComputeNode:
    node_id: str
    base_url: str
    witness_path: str = WITNESS_PATH
    trust_weight: float = 0.5
    default_provider: str = "mock"


def clear_peer_compute_cache() -> None:
    load_peer_compute_nodes.cache_clear()


def peer_compute_enabled() -> bool:
    env = os.getenv("ENABLE_PEER_COMPUTE", "").strip().lower()
    if env in ("true", "1", "yes", "on"):
        return True
    if env in ("false", "0", "no", "off"):
        return False
    registry = load_compute_registry()
    return bool((registry.get("peer_compute") or {}).get("enabled", False))


@lru_cache(maxsize=1)
def load_peer_compute_nodes() -> tuple[PeerComputeNode, ...]:
    registry = load_compute_registry()
    peer_cfg = registry.get("peer_compute") or {}
    nodes: list[PeerComputeNode] = []
    seen: set[str] = set()

    for item in peer_cfg.get("nodes") or []:
        if not isinstance(item, dict):
            continue
        node_id = str(item.get("node_id") or "").strip()
        base_url = str(item.get("base_url") or "").strip().rstrip("/")
        if not node_id or not base_url:
            continue
        seen.add(node_id)
        nodes.append(
            PeerComputeNode(
                node_id=node_id,
                base_url=base_url,
                witness_path=str(item.get("witness_path") or WITNESS_PATH),
                trust_weight=float(item.get("trust_weight") or 0.5),
                default_provider=str(item.get("default_provider") or "mock"),
            )
        )

    inherit = peer_cfg.get("inherit_trusted_nodes", True)
    if inherit:
        for trusted in load_trusted_nodes():
            if trusted.node_id in seen:
                continue
            seen.add(trusted.node_id)
            nodes.append(
                PeerComputeNode(
                    node_id=trusted.node_id,
                    base_url=trusted.base_url.rstrip("/"),
                    trust_weight=float(trusted.trust_weight),
                )
            )

    nodes.sort(key=lambda n: n.node_id)
    return tuple(nodes)


def select_peer_compute_node(strategy: str | None = None) -> PeerComputeNode | None:
    nodes = load_peer_compute_nodes()
    if not nodes:
        return None
    registry = load_compute_registry()
    strategy = strategy or (registry.get("peer_compute") or {}).get("routing") or "round_robin"
    if strategy == "highest_trust":
        return max(nodes, key=lambda n: n.trust_weight)
    idx = next(_round_robin) % len(nodes)
    return nodes[idx]


def peer_compute_secret() -> str | None:
    secret = os.getenv("POCP_PEER_COMPUTE_SECRET", "").strip()
    return secret or None


def peer_witness_allowed() -> bool:
    return os.getenv("POCP_ALLOW_PEER_WITNESS", "false").lower() in ("true", "1", "yes", "on")


def validate_peer_witness_request(headers: dict[str, str]) -> bool:
    if peer_witness_allowed():
        return True
    secret = peer_compute_secret()
    if secret and headers.get("x-pocp-peer-secret") == secret:
        return True
    from services.peer_trust import verify_peer_handshake

    result = verify_peer_handshake(headers)
    return result.ok


def probe_peer_compute(node: PeerComputeNode, timeout: float = 8.0) -> dict[str, Any]:
    import json
    import urllib.error
    import urllib.request

    root = node.base_url.rstrip("/")
    result: dict[str, Any] = {
        "node_id": node.node_id,
        "base_url": root,
        "reachable": False,
        "trust_weight": node.trust_weight,
    }
    try:
        with urllib.request.urlopen(f"{root}/api/v1/intelligence/compute/status", timeout=timeout) as resp:
            status = json.loads(resp.read().decode())
        result.update(
            {
                "reachable": True,
                "compute_status": status,
                "active_adapters": status.get("active_adapters") or [],
            }
        )
    except urllib.error.HTTPError as exc:
        result["error"] = f"HTTP {exc.code}"
    except Exception as exc:
        result["error"] = str(exc)
    return result


def list_peer_compute_status() -> dict[str, Any]:
    nodes = load_peer_compute_nodes()
    probes = [probe_peer_compute(n) for n in nodes]
    reachable = sum(1 for p in probes if p.get("reachable"))
    return {
        "peer_compute_enabled": peer_compute_enabled(),
        "routing": (load_compute_registry().get("peer_compute") or {}).get("routing", "round_robin"),
        "peer_count": len(nodes),
        "reachable_count": reachable,
        "peers": probes,
    }
