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


def clear_trusted_nodes_cache() -> None:
    load_trusted_nodes_from_yaml.cache_clear()


def is_node_trusted(node_id: str) -> bool:
    return node_id in trusted_nodes_map()


def append_trusted_node_to_yaml(node: TrustedNode, path: Path | None = None) -> bool:
    """Append a peer to trusted_nodes.yaml (idempotent). Returns True if newly added."""
    config_path = path or _CONFIG_PATH
    if config_path.exists():
        with config_path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    else:
        data = {"spec_version": "0.1", "trusted_nodes": []}

    nodes_raw = list(data.get("trusted_nodes") or [])
    if any(isinstance(n, dict) and n.get("node_id") == node.node_id for n in nodes_raw):
        return False

    entry: dict = {
        "node_id": node.node_id,
        "base_url": node.base_url.rstrip("/"),
        "trust_weight": float(node.trust_weight),
    }
    if node.public_key:
        entry["public_key"] = node.public_key
    if node.pqc_public_key:
        entry["pqc_public_key"] = node.pqc_public_key
    nodes_raw.append(entry)
    data["trusted_nodes"] = nodes_raw
    data.setdefault("spec_version", "0.1")

    config_path.parent.mkdir(parents=True, exist_ok=True)
    with config_path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)

    clear_trusted_nodes_cache()
    return True


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
