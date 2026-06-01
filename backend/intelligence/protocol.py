"""PoCP Unified Contribution Protocol — capability-layer primitives.

Principle: Everything connects through verified contribution.

Every Entity — human, agent, skill, LLM, tool, dataset, workflow, organization,
community — participates in the network through Contribution Events, not as passive
metadata rows.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

PROTOCOL_NAME = "PoCP Unified Contribution Protocol"
PROTOCOL_VERSION = "0.1"
CAPABILITY_LAYER_VERSION = "0.1"

UNIFIED_PRINCIPLE = "Everything connects through verified contribution."
UNIFIED_PRINCIPLE_ZH = "万物都有贡献，万物互联于贡献协议。"

# Accountability loop — intelligence advises; policy finalizes; ledger records (no human gate by default).
ACCOUNTABILITY_PRINCIPLE = "AI witnesses. Policy finalizes. Ledger remembers."
ACCOUNTABILITY_PRINCIPLE_ZH = "AI 见证，策略终局，账本记忆。"

# All entity types that the capability layer recognizes (synced with entity ontology v0.3).
def _entity_types() -> tuple[str, ...]:
    from intelligence.entity_ontology import all_entity_types

    return tuple(all_entity_types())


ENTITY_TYPES = _entity_types()

# Roles any entity may take in a contribution event (not all apply to every type).
CONTRIBUTION_ROLES = (
    "creator",
    "executor",
    "skill_provider",
    "tool_provider",
    "data_provider",
    "model_provider",
    "witness",
    "verifier",
    "reviewer",
    "coordinator",
    "sponsor",
)


class CapabilityModule(str, Enum):
    verification = "contribution_verification"
    reputation = "entity_reputation"
    matching = "skill_agent_matching"
    rewards = "cp_ai_credits_recommendation"
    anti_abuse = "anti_abuse_risk"
    graph = "contribution_graph"
    review_assistant = "human_review_assistant"
    governance = "governance_assistant"
    external_api = "external_intelligence_api"
    agent_runtime = "agent_runtime"


MODULE_DESCRIPTIONS: dict[CapabilityModule, str] = {
    CapabilityModule.verification: "Assess contribution authenticity and value; may auto-finalize under policy",
    CapabilityModule.reputation: "Compute and audit Human / Agent / Skill reputation",
    CapabilityModule.matching: "Recommend agents and skills for tasks",
    CapabilityModule.rewards: "Suggest CP and AI Credits from verified contribution",
    CapabilityModule.anti_abuse: "Evidence, limits, self-approval, duplicate detection",
    CapabilityModule.graph: "Build entity-centric contribution relationship graph",
    CapabilityModule.review_assistant: "Clarion-0 packets; advisory or delegated finalization (traceable)",
    CapabilityModule.governance: "Governance summaries and policy options (planned)",
    CapabilityModule.external_api: "Portable intelligence packets for third parties",
    CapabilityModule.agent_runtime: "Multi-step agent orchestration with InvocationTrace",
}


# Three-layer stack — engineering north star (see docs/PROTOCOL-STACK.md)
STACK_PROTOCOL = "protocol"
STACK_CAPABILITY = "capability"
STACK_TRANSACTION = "transaction"


def protocol_stack() -> dict[str, Any]:
    """Where PoCP engineering should invest — protocol & capability first, transaction last."""
    return {
        "north_star_zh": "在协议层与能力层建设，不在交易层堆功能。",
        "north_star": "Build at the protocol and capability layers; bind transactions thinly at the edge.",
        "layers": [
            {
                "id": STACK_PROTOCOL,
                "name": "Protocol Layer",
                "name_zh": "协议层",
                "owns": [
                    "Entity",
                    "Contribution Event",
                    "Contribution Participant",
                    "Evidence Hash",
                    "Human-AI Verification State",
                    "Finalization (traceable policy)",
                    "Contribution-to-Rights Conversion (versioned rules)",
                    "Capability Receipt (per invocation step)",
                    "InvocationTrace (portable)",
                    "Contribution Proof Packet",
                    "Contribution Graph semantics",
                    "Entity connection (structural / protocol / operational)",
                    "Trust Policy Bundle (federation import rules)",
                    "Portable identity (portable_id)",
                    "Federation trust & signed proofs",
                ],
                "spec": "PROTOCOL-SPEC-v0.1.md",
                "api_prefix": "/api/v1/intelligence/protocol",
                "build_here": True,
            },
            {
                "id": STACK_CAPABILITY,
                "name": "Capability Layer",
                "name_zh": "能力层",
                "owns": [
                    "Verification / witness consensus",
                    "Matching & agent runtime (StudyAgent, LangGraph)",
                    "Graph engine & analytics & federation intel",
                    "Review assistant (Clarion)",
                    "Governance advisory",
                    "Neural-source registry & embeddings",
                    "Intelligence packets (advisory JSON)",
                    "Semantic dedup hints",
                ],
                "sub_layers": [
                    {
                        "id": "distributed_intelligence",
                        "name": "Distributed Intelligence Layer",
                        "name_zh": "分布式智力层",
                        "owns": [
                            "Multi-LLM witness quorum",
                            "Agent runtime & InvocationTrace",
                            "Matching & graph analytics",
                            "Clarion / StudyAgent",
                        ],
                        "api_examples": [
                            "/api/v1/intelligence/match",
                            "/api/v1/intelligence/graph/analytics",
                            "/api/v1/intelligence/agents/study/run",
                        ],
                    },
                    {
                        "id": "distributed_compute",
                        "name": "Distributed Compute Layer",
                        "name_zh": "分布式算力层",
                        "owns": [
                            "Ollama / vLLM / OpenAI / DeepSeek adapters",
                            "sentence-transformers embeddings",
                            "compute_nodes registry & peer routing (NN-5)",
                        ],
                        "api_examples": [
                            "/api/v1/intelligence/compute/status",
                            "/api/v1/contributions/{id}/auto-verify",
                        ],
                        "config": "backend/config/compute_nodes.yaml",
                    },
                ],
                "code": "backend/intelligence/",
                "api_prefix": "/api/v1/intelligence",
                "build_here": True,
            },
            {
                "id": STACK_TRANSACTION,
                "name": "Transaction / Application Layer",
                "name_zh": "交易层（应用绑定）",
                "owns": [
                    "Wallet balances & credit_transactions",
                    "Approve / reject UI flows",
                    "OAuth sessions",
                    "Instance-specific task boards",
                ],
                "note": "Thin binding over protocol memory — not where PoCP differentiates.",
                "api_examples": [
                    "/api/v1/wallets",
                    "/api/v1/contributions/{id}/approve",
                    "/api/v1/ai/chat",
                ],
                "build_here": False,
            },
        ],
        "native_primitives": [
            "entity",
            "entity_connection",
            "trust_policy_bundle",
            "contribution_event",
            "contribution_participant",
            "evidence_hash",
            "verification_state",
            "contribution_proof_packet",
            "contribution_graph",
            "invocation_trace",
            "contribution_to_rights_conversion",
            "capability_receipt",
            "ledger_memory",
        ],
        "capability_modules": [m.value for m in CapabilityModule],
    }


def entity_can_contribute(entity_type: str) -> bool:
    """Every registered entity type may participate in contribution events."""
    return entity_type in ENTITY_TYPES


def contribution_packet_header() -> dict[str, Any]:
    from intelligence.entity_ontology import connection_matrix_document, ontology_document

    doc = ontology_document()
    connections = connection_matrix_document()
    return {
        "protocol": PROTOCOL_NAME,
        "protocol_version": PROTOCOL_VERSION,
        "capability_layer_version": CAPABILITY_LAYER_VERSION,
        "principle": UNIFIED_PRINCIPLE,
        "principle_zh": UNIFIED_PRINCIPLE_ZH,
        "entity_types": list(ENTITY_TYPES),
        "contribution_roles": list(CONTRIBUTION_ROLES),
        "entity_ontology": {
            "spec_version": doc["spec_version"],
            "docs": doc["docs"],
            "entity_type_count": len(doc["entity_types"]),
            "participant_role_count": len(doc["participant_roles"]),
        },
        "entity_connections": {
            "schema": "pocp.entity_connection.v0.1",
            "spec_version": connections["spec_version"],
            "layer_count": len(connections["layers"]),
            "matrix_api": "/api/v1/entities/connections/matrix",
            "instance_api": "/api/v1/entities/{entity_id}/connections",
            "docs": connections["docs"],
        },
    }
