"""REST/A2A → entity dialogue kind binding map (PL-5).

Canonical table: docs/protocol/BINDING-TO-DIALOGUE.md
Native semantics: pocp.entity_dialogue.v0.1 via route_dialogue; bindings are adapters.
"""

from __future__ import annotations

from typing import Any

BINDING_MAP_DOC = "docs/protocol/BINDING-TO-DIALOGUE.md"

# Entity ↔ Entity (same node) — mirrors BINDING-TO-DIALOGUE.md § Entity ↔ Entity (same node)
SAME_NODE_ENTITY_BINDINGS: tuple[dict[str, str], ...] = (
    {"binding": "POST /api/v1/intelligence/dialogue", "dialogue_kind": "*", "overlay": "via bridge"},
    {
        "binding": "POST /api/v1/intelligence/dialogue + payload.execute",
        "dialogue_kind": "invoke",
        "overlay": "InvocationCreated",
    },
    {"binding": "POST /api/v1/contributions", "dialogue_kind": "submit", "overlay": "ProofSubmitted"},
    {
        "binding": "POST /api/v1/contributions/{id}/auto-verify",
        "dialogue_kind": "attest",
        "overlay": "VerificationCompleted",
    },
    {"binding": "POST /api/v1/wallets/me/quote", "dialogue_kind": "quote", "overlay": "ExchangeQuoted"},
    {
        "binding": "POST /api/v1/capabilities/skills/{id}/execute",
        "dialogue_kind": "invoke",
        "overlay": "InvocationCreated",
    },
    {
        "binding": "POST /api/v1/capabilities/agents/{id}/execute",
        "dialogue_kind": "invoke",
        "overlay": "InvocationCreated",
    },
    {"binding": "POST /api/v1/invocations", "dialogue_kind": "invoke", "overlay": "InvocationCreated"},
    {
        "binding": "GET /api/v1/intelligence/entities/{id}/agent-card",
        "dialogue_kind": "discover",
        "overlay": "",
    },
    {
        "binding": "a2a.SendMessage",
        "dialogue_kind": "submit",
        "mode": "deferred",
        "overlay": "ProofSubmitted",
    },
)

A2A_SENDMESSAGE_BINDING_KEY = "a2a.SendMessage"
A2A_SENDMESSAGE_DIALOGUE_KIND = "submit"
A2A_DEFERRED_BINDING_MODE = "deferred"


def binding_map_manifest() -> dict[str, Any]:
    """Machine-readable slice of BINDING-TO-DIALOGUE for capability/A2A surfaces."""
    return {
        "doc": BINDING_MAP_DOC,
        "same_node_entity": list(SAME_NODE_ENTITY_BINDINGS),
        "a2a": {
            "SendMessage": {
                "dialogue_kind": A2A_SENDMESSAGE_DIALOGUE_KIND,
                "binding_mode": A2A_DEFERRED_BINDING_MODE,
                "overlay_event": "ProofSubmitted",
                "note": "Contribution via submit_contribution_event; full envelope route deferred.",
            },
            "GetTask": {"maps_to": "contribution_status", "dialogue_kind": None},
            "ListTasks": {"maps_to": "contribution_list", "dialogue_kind": None},
            "GetAgentCard": {"dialogue_kind": "discover", "binding_mode": "direct"},
        },
    }


def dialogue_kind_for_binding(binding_key: str) -> str | None:
    """Resolve dialogue kind for a binding key (e.g. a2a.SendMessage → submit)."""
    for row in SAME_NODE_ENTITY_BINDINGS:
        if row.get("binding") == binding_key:
            kind = row.get("dialogue_kind")
            return None if kind in ("*", "") else kind
    return None
