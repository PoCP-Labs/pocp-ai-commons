"""Frozen NodeProfile + well-known manifest schemas (CI-2 contract).

Aligned with:
- docs/protocol/NODE-RUNTIME-SPEC.md
- docs/protocol/PUBLIC-NODE-PROTOCOL.md
- models/node_profile.py (persistence)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

from services.entity.schemas import (
    BOB_REVIEWER_NODE_ID,
    INFRASTRUCTURE_ENTITY_IDS,
    LOCAL_COMPUTE_NODE_ID,
    LOCAL_VERIFIER_NODE_ID,
    PROTOCOL_TREASURY_ID,
    RAIN_SPONSOR_ID,
)

NODE_PROFILE_PROTOCOL_VERSION = "pocp-node-v0.1"
INSTANCE_MANIFEST_PROTOCOL = "pocp-node-manifest-v0.2-capability-first"
ENTITY_MANIFEST_PROTOCOL = INSTANCE_MANIFEST_PROTOCOL

NODE_TYPES = frozenset(
    {
        "light",
        "service",
        "compute",
        "verifier",
        "reviewer",
        "relay",
        "indexer",
        "governance",
        "treasury",
    }
)

NODE_STATUSES = frozenset({"registered", "active", "offline", "suspended"})

NODE_MODES = frozenset(
    {
        "direct_public",
        "reverse_proxy",
        "relay",
        "hosted",
        "offline_light",
    }
)

# CI-1 infrastructure IDs — canonical source: services/entity/schemas.py
CATALOG_INFRASTRUCTURE_ENTITY_IDS = INFRASTRUCTURE_ENTITY_IDS

CATALOG_NODE_TYPE_BY_ENTITY: dict[str, str] = {
    LOCAL_COMPUTE_NODE_ID: "compute",
    LOCAL_VERIFIER_NODE_ID: "verifier",
    BOB_REVIEWER_NODE_ID: "reviewer",
    RAIN_SPONSOR_ID: "service",
    PROTOCOL_TREASURY_ID: "treasury",
}


@dataclass(frozen=True)
class NodeProfileSchema:
    """Open-core NodeProfile — one primary profile per Entity."""

    node_id: str
    entity_id: str
    node_type: str
    did: str | None = None
    public_key: str | None = None
    base_url: str | None = None
    p2p_address: str | None = None
    health_url: str | None = None
    node_mode: str = "hosted"
    status: str = "registered"
    protocol_version: str = NODE_PROFILE_PROTOCOL_VERSION
    published_capabilities: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)
    last_heartbeat_at: datetime | None = None


@dataclass(frozen=True)
class PublicNodeEndpointSchema:
    """Derived public URLs for a registered node."""

    node_id: str
    entity_id: str
    base_url: str
    manifest_url: str
    health_url: str
    capabilities_url: str
    invoke_url: str
    proof_url: str
    settlement_ack_url: str
    status: str = "registered"


@dataclass(frozen=True)
class WellKnownInstanceManifestSchema:
    """GET /.well-known/pocp-node.json — instance host discovery."""

    protocol: str
    kind: Literal["instance"]
    instance_id: str
    display_name: str
    facets: tuple[str, ...]
    archive_entity_id: str
    endpoints: dict[str, str]
    updated_at: str


@dataclass(frozen=True)
class WellKnownEntityManifestSchema:
    """GET /api/v1/entities/{entity_id}/node-manifest — per-entity facet."""

    protocol: str
    kind: Literal["entity"]
    entity_id: str
    entity_type: str
    display_name: str
    status: str
    facets: tuple[str, ...]
    capabilities: tuple[dict[str, Any], ...]
    endpoints: dict[str, str]
    updated_at: str
    wallet_id: str | None = None
    description: str | None = None


INSTANCE_WELL_KNOWN_ENDPOINT_KEYS = frozenset(
    {
        "well_known",
        "health",
        "capabilities_directory",
        "ledger_verify",
        "federation_node",
    }
)

ENTITY_MANIFEST_ENDPOINT_KEYS = frozenset(
    {
        "manifest",
        "entity",
        "capabilities",
    }
)


def build_instance_endpoints(*, backend_url: str) -> dict[str, str]:
    """Canonical Phase A endpoint map for ``GET /.well-known/pocp-node.json``."""
    root = backend_url.rstrip("/")
    return {
        "well_known": f"{root}/.well-known/pocp-node.json",
        "health": f"{root}/health",
        "pocp_node": f"{root}/pocp/node",
        "pocp_health": f"{root}/pocp/health",
        "pocp_capabilities": f"{root}/pocp/capabilities",
        "pocp_invoke": f"{root}/pocp/invoke",
        "pocp_handshake": f"{root}/pocp/handshake",
        "pocp_proofs": f"{root}/pocp/proofs",
        "pocp_settlements_ack": f"{root}/pocp/settlements/ack",
        "pocp_sync": f"{root}/pocp/sync",
        "pocp_protocol": f"{root}/pocp/protocol",
        "capabilities_directory": f"{root}/api/v1/capabilities/directory",
        "ledger_verify": f"{root}/api/v1/ledger/verify",
        "federation_node": f"{root}/api/v1/federation/node",
    }


def catalog_node_specs(*, backend_url: str) -> tuple[tuple[str, str, str | None], ...]:
    """Infrastructure entity → (entity_id, node_type, base_url) for catalog bootstrap.

    Consumed by ``services/entity_catalog._ensure_node_profiles()`` — keep in sync
    with ``CATALOG_NODE_TYPE_BY_ENTITY``.
    """
    url_by_entity = {
        LOCAL_COMPUTE_NODE_ID: backend_url,
        LOCAL_VERIFIER_NODE_ID: backend_url,
    }
    return tuple(
        (entity_id, node_type, url_by_entity.get(entity_id))
        for entity_id, node_type in CATALOG_NODE_TYPE_BY_ENTITY.items()
    )


def validate_node_type(node_type: str) -> None:
    if node_type not in NODE_TYPES:
        raise ValueError(f"Invalid node_type {node_type!r}; expected one of {sorted(NODE_TYPES)}")


def validate_node_profile(profile: dict[str, Any]) -> None:
    """Raise ValueError when a NodeProfile dict violates the frozen v0.1 contract."""
    required = ("node_id", "entity_id", "node_type", "protocol_version")
    missing = [key for key in required if key not in profile]
    if missing:
        raise ValueError(f"NodeProfile missing fields: {missing}")
    validate_node_type(profile["node_type"])
    if profile["protocol_version"] != NODE_PROFILE_PROTOCOL_VERSION:
        raise ValueError(f"Unexpected protocol_version: {profile['protocol_version']!r}")
    status = profile.get("status", "registered")
    if status not in NODE_STATUSES:
        raise ValueError(f"Invalid status {status!r}")
    node_mode = profile.get("node_mode", "hosted")
    if node_mode not in NODE_MODES:
        raise ValueError(f"Invalid node_mode {node_mode!r}")


def node_profile_as_dict(profile: NodeProfileSchema) -> dict[str, Any]:
    """Serialize a frozen NodeProfileSchema for API / manifest consumers."""
    return {
        "node_id": profile.node_id,
        "entity_id": profile.entity_id,
        "node_type": profile.node_type,
        "did": profile.did,
        "public_key": profile.public_key,
        "base_url": profile.base_url,
        "p2p_address": profile.p2p_address,
        "health_url": profile.health_url,
        "node_mode": profile.node_mode,
        "status": profile.status,
        "protocol_version": profile.protocol_version,
        "published_capabilities": list(profile.published_capabilities),
        "metadata": dict(profile.metadata),
        "last_heartbeat_at": (
            profile.last_heartbeat_at.isoformat() if profile.last_heartbeat_at else None
        ),
    }


def validate_well_known_instance(manifest: dict[str, Any]) -> None:
    """Raise ValueError when a well-known instance manifest violates the frozen contract."""
    required = ("protocol", "kind", "instance_id", "display_name", "facets", "archive_entity_id", "endpoints", "updated_at")
    missing = [key for key in required if key not in manifest]
    if missing:
        raise ValueError(f"Well-known instance manifest missing fields: {missing}")
    if manifest["protocol"] != INSTANCE_MANIFEST_PROTOCOL:
        raise ValueError(f"Unexpected protocol: {manifest['protocol']!r}")
    if manifest["kind"] != "instance":
        raise ValueError(f"Unexpected kind: {manifest['kind']!r}")
    endpoints = manifest["endpoints"]
    if not isinstance(endpoints, dict):
        raise ValueError("endpoints must be an object")
    missing_eps = INSTANCE_WELL_KNOWN_ENDPOINT_KEYS - set(endpoints)
    if missing_eps:
        raise ValueError(f"Well-known endpoints missing keys: {sorted(missing_eps)}")


def validate_well_known_entity(manifest: dict[str, Any]) -> None:
    """Raise ValueError when a per-entity node manifest violates the frozen contract."""
    required = (
        "protocol",
        "kind",
        "entity_id",
        "entity_type",
        "display_name",
        "status",
        "facets",
        "capabilities",
        "endpoints",
        "updated_at",
    )
    missing = [key for key in required if key not in manifest]
    if missing:
        raise ValueError(f"Entity node manifest missing fields: {missing}")
    if manifest["protocol"] != ENTITY_MANIFEST_PROTOCOL:
        raise ValueError(f"Unexpected protocol: {manifest['protocol']!r}")
    if manifest["kind"] != "entity":
        raise ValueError(f"Unexpected kind: {manifest['kind']!r}")
    endpoints = manifest["endpoints"]
    if not isinstance(endpoints, dict):
        raise ValueError("endpoints must be an object")
    missing_eps = ENTITY_MANIFEST_ENDPOINT_KEYS - set(endpoints)
    if missing_eps:
        raise ValueError(f"Entity manifest endpoints missing keys: {sorted(missing_eps)}")
    if not isinstance(manifest["capabilities"], list):
        raise ValueError("capabilities must be an array")
