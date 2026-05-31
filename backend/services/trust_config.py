"""Load and validate federated trust configuration (YAML + env override)."""

import hashlib
import json
import os
from functools import lru_cache
from pathlib import Path

import yaml

from schemas.federation import TrustedNode

_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "trusted_nodes.yaml"


def _parse_nodes(items: list) -> list[TrustedNode]:
    nodes: list[TrustedNode] = []
    for item in items:
        if isinstance(item, dict) and item.get("node_id") and item.get("base_url"):
            nodes.append(TrustedNode(**item))
    return nodes


@lru_cache(maxsize=1)
def load_trusted_nodes_from_yaml(path: Path | None = None) -> list[TrustedNode]:
    config_path = path or _CONFIG_PATH
    if not config_path.exists():
        return []
    with config_path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return _parse_nodes(data.get("trusted_nodes") or [])


def load_trusted_nodes_from_env() -> list[TrustedNode]:
    raw = os.getenv("POCP_TRUSTED_NODES", "").strip()
    if not raw:
        return []
    try:
        items = json.loads(raw)
    except json.JSONDecodeError:
        return []
    return _parse_nodes(items if isinstance(items, list) else [])


def load_trusted_nodes() -> list[TrustedNode]:
    """Env overrides YAML when POCP_TRUSTED_NODES is set."""
    env_nodes = load_trusted_nodes_from_env()
    if env_nodes:
        return env_nodes
    return load_trusted_nodes_from_yaml()


def trusted_nodes_map() -> dict[str, TrustedNode]:
    return {node.node_id: node for node in load_trusted_nodes()}


def trusted_nodes_source() -> str:
    if load_trusted_nodes_from_env():
        return "env"
    if load_trusted_nodes_from_yaml():
        return "yaml"
    return "none"


def canonical_trust_payload(nodes: list[TrustedNode] | None = None) -> list[dict]:
    items = nodes if nodes is not None else load_trusted_nodes()
    return sorted(
        [
            {
                "node_id": n.node_id,
                "base_url": n.base_url.rstrip("/"),
                "public_key": n.public_key or "",
                "pqc_public_key": n.pqc_public_key or "",
                "trust_weight": round(float(n.trust_weight), 4),
            }
            for n in items
        ],
        key=lambda x: x["node_id"],
    )


def trust_list_hash(nodes: list[TrustedNode] | None = None) -> str:
    payload = canonical_trust_payload(nodes)
    material = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(material.encode("utf-8")).hexdigest()
