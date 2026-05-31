"""HTTP client utilities for federated peer nodes."""

import json
import os
import urllib.error
import urllib.request

from schemas.federation import TrustedNode
from services.trust_config import load_trusted_nodes, trusted_nodes_map


def trusted_nodes_map() -> dict[str, TrustedNode]:
    return {node.node_id: node for node in load_trusted_nodes()}


def _get_json(url: str, timeout: float = 20.0) -> dict | list:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.loads(response.read().decode())


def _post_json(url: str, body: dict, timeout: float = 30.0) -> dict:
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode())


def probe_peer(base_url: str) -> dict:
    root = base_url.rstrip("/")
    result: dict = {"base_url": root, "reachable": False}
    try:
        health = _get_json(f"{root}/health")
        node = _get_json(f"{root}/api/v1/federation/node")
        ledger_verify = _get_json(f"{root}/api/v1/ledger/verify")
        anchor = _get_json(f"{root}/api/v1/ledger/anchor")
        result.update(
            {
                "reachable": True,
                "health": health,
                "node": node,
                "ledger_valid": ledger_verify.get("valid"),
                "ledger_count": ledger_verify.get("count"),
                "anchor_merkle_root": anchor.get("merkle_root"),
                "anchor_tip_hash": anchor.get("tip_hash"),
            }
        )
    except urllib.error.HTTPError as exc:
        result["error"] = f"HTTP {exc.code}: {exc.read().decode()}"
    except urllib.error.URLError as exc:
        result["error"] = str(exc.reason)
    except Exception as exc:
        result["error"] = str(exc)
    return result


def verify_remote_ledger(base_url: str, expected_tip_hash: str | None = None) -> None:
    """Raise ValueError if remote ledger is invalid or tip hash mismatches."""
    root = base_url.rstrip("/")
    verify = _get_json(f"{root}/api/v1/ledger/verify")
    if not verify.get("valid"):
        raise ValueError(f"Remote ledger invalid at {root}")

    if not expected_tip_hash:
        return

    anchor = _get_json(f"{root}/api/v1/ledger/anchor")
    tip = anchor.get("tip_hash")
    if tip and tip != expected_tip_hash:
        raise ValueError("Remote ledger tip_hash does not match proof ledger_tip_hash")


def verify_remote_ledger_record(base_url: str, record_hash: str | None) -> None:
    """Ensure remote ledger chain is valid and contains the signed approval record."""
    if not record_hash:
        raise ValueError("Proof missing ledger record hash for verification")
    root = base_url.rstrip("/")
    verify = _get_json(f"{root}/api/v1/ledger/verify")
    if not verify.get("valid"):
        raise ValueError(f"Remote ledger invalid at {root}")
    export = _get_json(f"{root}/api/v1/ledger/export")
    known = {row.get("record_hash") for row in export.get("records", []) if row.get("record_hash")}
    if record_hash not in known:
        raise ValueError(f"Remote ledger missing approval record_hash {record_hash[:16]}…")


def fetch_proof(base_url: str, contribution_id: str) -> dict:
    return _get_json(f"{base_url.rstrip('/')}/api/v1/contributions/{contribution_id}/proof")


def fetch_federation_intelligence(base_url: str, contribution_id: str) -> dict | None:
    """Fetch intelligence + proof bundle from a peer (optional during sync)."""
    root = base_url.rstrip("/")
    try:
        return _get_json(f"{root}/api/v1/intelligence/federation/export/{contribution_id}")
    except Exception:
        return None


def post_import_proof(target_base_url: str, source_node_id: str, proof: dict) -> dict:
    return _post_json(
        f"{target_base_url.rstrip('/')}/api/v1/federation/import-proof",
        {"source_node_id": source_node_id, "proof": proof},
    )
