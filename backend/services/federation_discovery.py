"""CI-5 — federation peer manifests, capability discovery, and trust handshake."""

from __future__ import annotations

import os
from typing import Any

from services.federation_peers import _get_json, probe_peer
from services.peer_trust import peer_trust_manifest
from services.trust_policy_bundle import bundle_fingerprint, trust_policy_bundle_manifest

FEDERATION_PEER_MANIFEST_SCHEMA = "pocp.federation_peer_manifest.v0.1"
PUBLIC_SKILL_NODE_TEMPLATE_SCHEMA = "pocp-skill-node-template.v0.1"


def public_skill_node_template() -> dict[str, Any]:
    """Reference template for a public skill node (MINIMUM-LIVING-NETWORK step 2)."""
    return {
        "schema": PUBLIC_SKILL_NODE_TEMPLATE_SCHEMA,
        "spec_version": "0.1",
        "node_type": "service",
        "roles": ["skill_provider", "public_node"],
        "entity_types": ["skill", "service"],
        "default_capability": {
            "capability_type": "code_review",
            "name": "Python Code Review",
            "unit": "skill_invocation",
            "price_model": "fixed",
            "base_price": 5.0,
            "accepted_units": ["AIC"],
            "verification_method": "human_review",
        },
        "endpoints": {
            "well_known": "/.well-known/pocp-node.json",
            "agent_card": "/.well-known/agent.json",
            "health": "/pocp/health",
            "capabilities": "/pocp/capabilities",
            "handshake": "/pocp/handshake",
            "invoke": "/pocp/invoke",
            "proofs": "/pocp/proofs",
        },
        "federation_surface": {
            "node": "/api/v1/federation/node",
            "peer_manifest": "/api/v1/federation/peers/manifest",
            "handshake": "/api/v1/federation/peers/handshake",
            "trust_policy_bundle": "/api/v1/federation/trust-policy-bundle",
            "capability_search": "/api/v1/registry/capabilities",
        },
        "minimum_living_network_steps": [2, 3, 4],
    }


def build_local_peer_manifest(*, base_url: str | None = None) -> dict[str, Any]:
    """Aggregate local federation discovery surface for peers (CI-5 manifest)."""
    from services.federation_crypto import get_node_public_key_hex
    from services.crypto_suite import active_crypto_suite
    from services.node_mode import node_mode

    root = (base_url or os.getenv("BACKEND_URL", "http://localhost:8000")).rstrip("/")
    node_id = os.getenv("POCP_NODE_ID", "pocp-node-local")
    bundle = trust_policy_bundle_manifest()
    handshake = peer_trust_manifest()
    return {
        "schema": FEDERATION_PEER_MANIFEST_SCHEMA,
        "spec_version": "0.1",
        "node_id": node_id,
        "base_url": root,
        "crypto_suite": active_crypto_suite(),
        "node_mode": node_mode(),
        "public_key": get_node_public_key_hex(),
        "trust_policy_bundle_fingerprint": bundle.get("bundle_fingerprint"),
        "trust_policy_bundle_schema": bundle.get("schema"),
        "handshake": handshake,
        "well_known": {
            "pocp_node": f"{root}/.well-known/pocp-node.json",
            "agent_card": f"{root}/.well-known/agent.json",
        },
        "discovery": {
            "capability_search": f"{root}/api/v1/registry/capabilities",
            "skill_node_template_schema": PUBLIC_SKILL_NODE_TEMPLATE_SCHEMA,
            "skill_node_template_path": "/api/v1/federation/skill-node-template",
        },
        "skill_node_template": public_skill_node_template(),
    }


def fetch_remote_peer_manifest(base_url: str) -> dict[str, Any]:
    """Fetch a peer's published federation manifest."""
    root = base_url.rstrip("/")
    try:
        return _get_json(f"{root}/api/v1/federation/peers/manifest")
    except Exception:
        pass
    probe = probe_peer(root)
    if not probe.get("reachable"):
        raise ValueError(probe.get("error") or f"Peer not reachable at {root}")
    node = probe.get("node") or {}
    bundle = _get_json(f"{root}/api/v1/federation/trust-policy-bundle")
    handshake = _get_json(f"{root}/api/v1/intelligence/compute/peer/trust")
    return {
        "schema": FEDERATION_PEER_MANIFEST_SCHEMA,
        "spec_version": "0.1",
        "node_id": node.get("node_id"),
        "base_url": root,
        "crypto_suite": node.get("crypto_suite"),
        "node_mode": node.get("node_mode"),
        "public_key": node.get("public_key"),
        "trust_policy_bundle_fingerprint": bundle.get("bundle_fingerprint"),
        "trust_policy_bundle_schema": bundle.get("schema"),
        "handshake": handshake,
        "probe": {
            "ledger_valid": probe.get("ledger_valid"),
            "ledger_count": probe.get("ledger_count"),
        },
        "well_known": {
            "pocp_node": f"{root}/.well-known/pocp-node.json",
            "agent_card": f"{root}/.well-known/agent.json",
        },
        "discovery": {
            "capability_search": f"{root}/api/v1/registry/capabilities",
        },
    }


def discover_peer_capabilities(
    base_url: str,
    *,
    capability_type: str | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    """MLN step 3 — search a peer's public capability registry."""
    root = base_url.rstrip("/")
    params = f"?limit={limit}"
    if capability_type:
        params += f"&capability_type={capability_type}"
    try:
        payload = _get_json(f"{root}/api/v1/registry/capabilities{params}")
    except Exception as exc:
        raise ValueError(f"Capability discovery failed at {root}: {exc}") from exc
    items = payload.get("capabilities") or payload.get("items") or []
    if isinstance(payload, list):
        items = payload
    return {
        "schema": "pocp.federation_capability_discover.v0.1",
        "peer_base_url": root,
        "capability_type": capability_type,
        "count": len(items),
        "capabilities": items,
    }


def federation_handshake_with_peer(
    base_url: str,
    *,
    require_trust_bundle_match: bool = False,
) -> dict[str, Any]:
    """MLN step 4 — probe peer, align trust bundle fingerprint, verify handshake surface."""
    root = base_url.rstrip("/")
    local_fp = bundle_fingerprint()
    remote = fetch_remote_peer_manifest(root)
    remote_node_id = remote.get("node_id")
    if not remote_node_id:
        raise ValueError("Remote peer manifest missing node_id")

    remote_fp = remote.get("trust_policy_bundle_fingerprint")
    bundle_aligned = bool(remote_fp) and remote_fp == local_fp
    handshake = remote.get("handshake") or {}
    algorithms = handshake.get("algorithms") or []
    handshake_ok = bool(handshake.get("handshake_version")) and bool(algorithms)

    if require_trust_bundle_match and not bundle_aligned:
        raise ValueError(
            f"Trust bundle fingerprint mismatch local={local_fp} remote={remote_fp}"
        )
    if not handshake_ok:
        raise ValueError("Remote peer missing handshake manifest or algorithms")

    return {
        "schema": "pocp.federation_handshake.v0.1",
        "ok": True,
        "local_node_id": os.getenv("POCP_NODE_ID", "pocp-node-local"),
        "remote_node_id": remote_node_id,
        "remote_base_url": root,
        "trust_bundle_aligned": bundle_aligned,
        "local_bundle_fingerprint": local_fp,
        "remote_bundle_fingerprint": remote_fp,
        "handshake_version": handshake.get("handshake_version"),
        "algorithms": algorithms,
        "handshake_mode": handshake.get("handshake_mode"),
        "challenge_endpoint": handshake.get("challenge_endpoint"),
    }
