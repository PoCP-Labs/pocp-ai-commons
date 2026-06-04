"""Frozen operator manifest fragments for federation + public node surfaces (CIP-P0.2).

Consumed by ``services.protocol_federation_status.federation_protocol_manifest``.
Spec: ``docs/protocol/BINDING-TO-DIALOGUE.md`` · ``docs/protocol/PUBLIC-NODE-PROTOCOL.md``.
"""

from __future__ import annotations

from typing import Any

from services.node.schemas import build_instance_endpoints

FEDERATION_PROTOCOL_MANIFEST_SCHEMA = "pocp.federation_protocol_manifest.v0.1"


def build_pocp_public_surface(*, backend_url: str) -> dict[str, Any]:
    """Phase A ``/pocp/*`` shim — aliases over existing federation + dialogue routes."""
    root = backend_url.rstrip("/")
    endpoints = build_instance_endpoints(backend_url=root)
    return {
        "schema": "pocp.public_node_protocol.v0.1",
        "spec": "docs/protocol/PUBLIC-NODE-PROTOCOL.md",
        "manifest_api": f"{root}/pocp/protocol",
        "endpoints": endpoints,
        "routes": {
            "GET /pocp/node": "instance manifest + endpoint map",
            "GET /pocp/health": "liveness",
            "GET /pocp/capabilities": "provider directory",
            "GET /pocp/protocol": "self-describing route map",
            "GET /pocp/sync": "local peer manifest; ?run=true sync trusted peers",
            "POST /pocp/handshake": "federation peer handshake",
            "POST /pocp/invoke": "entity dialogue (pocp.entity_dialogue.v0.1)",
            "POST /pocp/proofs": "verify portable proof packet",
            "POST /pocp/settlements/ack": "federation settlement intent",
        },
        "legacy_bindings": {
            "well_known": "/.well-known/pocp-node.json",
            "federation_dialogue": "/api/v1/federation/dialogue",
            "capabilities_directory": "/api/v1/capabilities/directory",
        },
    }


def build_exchange_import_surface() -> dict[str, Any]:
    """L1 federation exchange proof import — verify-only, no BC mint on importer."""
    return {
        "schema": "pocp.federation_exchange_import.v0.1",
        "spec": "docs/protocol/TRUST-POLICY-BUNDLE.md",
        "service": "backend/services/federation_exchange_import.py",
        "acceptance_levels": ("L0", "L1", "L2", "L3"),
        "default_acceptance": "L1",
        "endpoints": {
            "import_exchange_proof": "POST /api/v1/federation/import-exchange-proof",
            "import_proof": "POST /api/v1/federation/import-proof",
            "validate_proof": "POST /api/v1/federation/validate-proof",
            "import_event": "POST /api/v1/federation/import",
            "list_imports": "GET /api/v1/federation/imports",
        },
        "dialogue_kinds": {
            "federation_offer": "proof deref / offer before import",
            "federation_accept": "native import mirror (preferred over raw REST)",
        },
        "env": [
            "POCP_REQUIRE_IMPORT_SIGNATURE",
            "POCP_ALLOW_UNTRUSTED_IMPORT",
            "POCP_SIGN_COMPUTE_RECEIPTS",
            "POCP_STAGING_FEDERATION_NODE_A",
            "POCP_STAGING_FEDERATION_NODE_B",
        ],
    }


def build_metered_binding_surface() -> dict[str, Any]:
    """REST bindings that must emit ``exchange_settled`` (see EXCHANGE-SPINE-v0.1)."""
    return {
        "schema": "pocp.binding_to_dialogue.v0.1",
        "spec": "docs/protocol/BINDING-TO-DIALOGUE.md",
        "bindings": [
            {
                "binding": "POST /api/v1/ai/chat",
                "dialogue_kind": "invoke",
                "exchange_kind": "capability",
                "legacy_event_type": "ai_chat",
                "receipt": "CapabilityReceipt via exchange_spine",
            },
            {
                "binding": "POST /api/v1/capabilities/mcp/{tool_entity_id}/invoke",
                "dialogue_kind": "invoke",
                "exchange_kind": "capability",
                "capability": "mcp_tool_call",
                "receipt": "CapabilityReceipt + security_audit",
            },
            {
                "binding": "POST /api/v1/intelligence/compute/mcp/invoke",
                "dialogue_kind": "invoke",
                "exchange_kind": "capability",
                "capability": "mcp_tool_call",
                "note": "remote MCP peer path",
            },
            {
                "binding": "POST /api/v1/intelligence/dialogue",
                "dialogue_kind": "invoke",
                "exchange_kind": "capability",
                "execute_flag": "payload.execute=true",
                "receipt": "CapabilityReceipt via dialogue_invoke",
            },
            {
                "binding": "POST /api/v1/intelligence/entities/{entity_id}/dialogue",
                "dialogue_kind": "invoke",
                "exchange_kind": "capability",
                "execute_flag": "payload.execute=true",
            },
            {
                "binding": "POST /api/v1/federation/dialogue",
                "dialogue_kind": "invoke | quote | …",
                "exchange_kind": "capability",
                "execute_flag": "payload.execute=true",
            },
            {
                "binding": "POST /pocp/invoke",
                "dialogue_kind": "invoke | quote | ping",
                "exchange_kind": "capability",
                "execute_flag": "payload.execute=true",
                "note": "public node alias — same semantics as federation/dialogue",
            },
            {
                "binding": "POST /api/v1/capabilities/skills/{id}/execute",
                "dialogue_kind": "invoke",
                "exchange_kind": "capability | hybrid",
            },
            {
                "binding": "POST /api/v1/capabilities/agents/{id}/execute",
                "dialogue_kind": "invoke",
                "exchange_kind": "capability | hybrid",
            },
            {
                "binding": "POST /api/v1/wallets/me/quote",
                "dialogue_kind": "quote",
                "exchange_kind": "capability",
                "overlay_event": "ExchangeQuoted",
            },
        ],
    }


def federation_operator_manifest_extensions(*, backend_url: str) -> dict[str, Any]:
    """Keys merged into ``GET /api/v1/intelligence/protocol/federation``."""
    root = backend_url.rstrip("/")
    instance_eps = build_instance_endpoints(backend_url=root)
    return {
        "operator_manifest": {
            "schema": FEDERATION_PROTOCOL_MANIFEST_SCHEMA,
            "stack_api": f"{root}/api/v1/intelligence/protocol/stack",
            "federation_api": f"{root}/api/v1/intelligence/protocol/federation",
            "well_known": instance_eps.get("well_known"),
            "quote": "POST /api/v1/wallets/me/quote",
            "invoke": instance_eps.get("pocp_invoke") or f"{root}/pocp/invoke",
            "receipt": "CapabilityReceipt on execute bindings (include_receipt=true on REST)",
            "federation_connect": instance_eps.get("pocp_handshake") or f"{root}/pocp/handshake",
            "exchange_proof_import": "POST /api/v1/federation/import-exchange-proof",
        },
        "public_node": build_pocp_public_surface(backend_url=root),
        "exchange_import": build_exchange_import_surface(),
        "metered_bindings": build_metered_binding_surface(),
    }
