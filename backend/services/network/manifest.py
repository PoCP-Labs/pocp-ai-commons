"""Protocol Event Network overlay manifest."""

from __future__ import annotations

from typing import Any

from services.network.protocol_bridge import DIALOGUE_TO_EVENT_TYPE, PROTOCOL_EVENT_SCHEMA


def network_overlay_manifest() -> dict[str, Any]:
    return {
        "schema": PROTOCOL_EVENT_SCHEMA,
        "spec_version": "0.2",
        "stack_layer": "L1.5_overlay",
        "stack_layer_zh": "协议事件覆盖层",
        "principle": "Hash-linked ProtocolEvents over HTTPS — no PoCP physical network.",
        "principle_zh": "在现有 Internet 上传播 ProtocolEvent，不建自有物理网。",
        "dialogue_to_event_type": DIALOGUE_TO_EVENT_TYPE,
        "components": {
            "mempool": "PoCPMempool",
            "event_batch": "EventBatchService",
            "merkle": "MerkleService",
            "confirmation": "ConfirmationService",
            "peer_registry": "PeerRegistry",
        },
        "endpoints": {
            "manifest": "/api/v1/intelligence/protocol/network",
            "status": "/api/v1/intelligence/network/overlay/status",
            "events": "/api/v1/intelligence/network/overlay/events",
            "events_list": "GET /api/v1/intelligence/network/overlay/events",
            "batch": "/api/v1/intelligence/network/overlay/batch",
            "demo": "/api/v1/intelligence/network/overlay/demo",
            "gossip_receive": "/api/v1/intelligence/network/overlay/gossip/receive",
            "gossip_push": "POST /api/v1/intelligence/network/overlay/gossip/push",
        },
        "docs": {
            "overview": "docs/protocol/PROTOCOL-EVENT-NETWORK.md",
            "bitcoin_inspired": "BITCOIN-INSPIRED-POCP-NETWORK.md",
            "binding_map": "docs/protocol/BINDING-TO-DIALOGUE.md",
            "entity_dialogue": "docs/protocol/ENTITY-DIALOGUE-PROTOCOL.md",
        },
        "smoke": "python backend/scripts/bitcoin_inspired_network_smoke.py",
    }
