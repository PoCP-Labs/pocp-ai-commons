"""Canonical Entity ontology — types, roles, accountability, and metadata contracts.

See docs/ENTITY-ONTOLOGY.md
"""

from __future__ import annotations

from typing import Any

# Network subject types (protocol v0.1)
ENTITY_TYPE_SPECS: dict[str, dict[str, Any]] = {
    "human": {
        "label": "Human",
        "label_zh": "人类",
        "network_subject": True,
        "accountable_principal": True,
        "can_own_entities": True,
        "typical_roles": ["creator", "reviewer", "coordinator", "sponsor"],
        "description": "Accountability anchor — may create, review, govern, and bear final responsibility.",
        "description_zh": "责任锚点 — 可创造、终审、治理并承担最终责任。",
    },
    "agent": {
        "label": "Agent",
        "label_zh": "智能体",
        "network_subject": True,
        "accountable_principal": False,
        "can_own_entities": False,
        "typical_roles": ["executor", "coordinator"],
        "description": "Multi-step executor — orchestrates skills, tools, and LLM calls.",
        "description_zh": "多步执行体 — 编排 Skill、Tool 与 LLM 调用。",
        "metadata_keys": ["capabilities", "service_endpoints", "runtime", "registry_compat"],
    },
    "skill": {
        "label": "Skill",
        "label_zh": "技能",
        "network_subject": True,
        "accountable_principal": False,
        "can_own_entities": False,
        "typical_roles": ["skill_provider"],
        "description": "Reusable capability module — AgentSkills / prompt / OpenClaw skill.",
        "description_zh": "可复用能力模块 — AgentSkills / prompt / OpenClaw skill。",
        "metadata_keys": ["capability_source", "agentskills_compat", "runtime", "frontmatter"],
    },
    "llm": {
        "label": "LLM",
        "label_zh": "大模型",
        "network_subject": True,
        "accountable_principal": False,
        "can_own_entities": False,
        "typical_roles": ["model_provider", "witness", "verifier"],
        "description": "Model witness — inference, advisory verification, chat; not final judge.",
        "description_zh": "模型见证 — 推理、建议性验证、对话；非最终裁判。",
        "metadata_keys": ["roles", "counterpart", "governance_note", "mission"],
    },
    "tool": {
        "label": "Tool",
        "label_zh": "工具",
        "network_subject": True,
        "accountable_principal": False,
        "can_own_entities": False,
        "typical_roles": ["tool_provider"],
        "description": "Callable tool — MCP server, API, CLI, browser, Git, calculator.",
        "description_zh": "可调用工具 — MCP 服务、API、CLI、浏览器、Git 等。",
        "metadata_keys": ["tool_kind", "service_endpoints", "mcp_server", "capabilities"],
    },
    "dataset": {
        "label": "Dataset",
        "label_zh": "数据集",
        "network_subject": True,
        "accountable_principal": False,
        "can_own_entities": False,
        "typical_roles": ["data_provider"],
        "description": "Structured knowledge or corpus cited or used in contribution evidence.",
        "description_zh": "在贡献证据中被引用或使用结构化知识/语料。",
        "metadata_keys": ["source_uri", "license", "content_hash", "format"],
    },
    "workflow": {
        "label": "Workflow",
        "label_zh": "工作流",
        "network_subject": True,
        "accountable_principal": False,
        "can_own_entities": False,
        "typical_roles": ["coordinator"],
        "description": "Reusable multi-step process template coordinating entities.",
        "description_zh": "协调多 Entity 的可复用流程模板。",
        "metadata_keys": ["steps", "version", "entrypoint"],
    },
    "organization": {
        "label": "Organization",
        "label_zh": "组织",
        "network_subject": True,
        "accountable_principal": True,
        "can_own_entities": True,
        "typical_roles": ["sponsor", "coordinator"],
        "description": "Org container — tasks, sponsorship, governance proxy.",
        "description_zh": "组织容器 — 任务、赞助、治理代理。",
        "metadata_keys": ["org_type", "governance_proxy_id", "mission"],
    },
    "community": {
        "label": "Community",
        "label_zh": "社区",
        "network_subject": True,
        "accountable_principal": False,
        "can_own_entities": False,
        "typical_roles": ["sponsor", "witness"],
        "description": "Community memory — patterns, federation peers, external inspirations.",
        "description_zh": "社区记忆 — 模式借用、联邦节点、外部灵感实体。",
        "metadata_keys": ["roles", "portable_id", "pattern_borrowed"],
    },
    "compute_node": {
        "label": "Compute Node",
        "label_zh": "算力节点",
        "network_subject": True,
        "accountable_principal": False,
        "can_own_entities": False,
        "typical_roles": ["model_provider", "tool_provider"],
        "description": "GPU/CPU provider — inference, training, embeddings, witness compute.",
        "description_zh": "GPU/CPU 提供者 — 推理、训练、嵌入、见证算力。",
        "metadata_keys": ["compute_profile", "region", "hardware", "capabilities", "verification_methods"],
    },
    "verifier_node": {
        "label": "Verifier Node",
        "label_zh": "验证节点",
        "network_subject": True,
        "accountable_principal": False,
        "can_own_entities": False,
        "typical_roles": ["verifier", "witness"],
        "description": "Dedicated verification service — AI, peer, or hybrid witness.",
        "description_zh": "专用验证服务 — AI、对等或混合见证。",
        "metadata_keys": ["verifier_kinds", "service_endpoints", "trust_level"],
    },
    "reviewer_node": {
        "label": "Reviewer Node",
        "label_zh": "审查节点",
        "network_subject": True,
        "accountable_principal": False,
        "can_own_entities": False,
        "typical_roles": ["reviewer"],
        "description": "Human or agent review queue endpoint — advisory, not black-box finalizer.",
        "description_zh": "人工或 Agent 审查队列端点 — 建议性，非黑盒终局。",
        "metadata_keys": ["review_policy", "queue_capacity", "supported_task_types"],
    },
    "sponsor": {
        "label": "Sponsor",
        "label_zh": "赞助实体",
        "network_subject": True,
        "accountable_principal": True,
        "can_own_entities": True,
        "typical_roles": ["sponsor"],
        "description": "Funding pool or bounty sponsor — may deposit credits for tasks.",
        "description_zh": "资金池或悬赏赞助 — 可为任务注入 Credits。",
        "metadata_keys": ["pool_balance", "sponsor_policy", "accepted_units"],
    },
    "protocol_treasury": {
        "label": "Protocol Treasury",
        "label_zh": "协议金库",
        "network_subject": True,
        "accountable_principal": True,
        "can_own_entities": False,
        "typical_roles": ["sponsor"],
        "description": "Protocol-level treasury — fees, reserves, governance-controlled flows.",
        "description_zh": "协议级金库 — 费用、储备、治理控制的流转。",
        "metadata_keys": ["treasury_policy", "fee_schedule", "governance_entity_id"],
    },
}

PARTICIPANT_ROLE_SPECS: dict[str, dict[str, Any]] = {
    "creator": {
        "label": "Creator",
        "label_zh": "创造者",
        "description": "Primary author or initiator of the contribution value.",
    },
    "executor": {
        "label": "Executor",
        "label_zh": "执行者",
        "typical_entity_types": ["agent", "human"],
    },
    "skill_provider": {
        "label": "Skill provider",
        "label_zh": "技能提供者",
        "typical_entity_types": ["skill"],
    },
    "tool_provider": {
        "label": "Tool provider",
        "label_zh": "工具提供者",
        "typical_entity_types": ["tool"],
    },
    "data_provider": {
        "label": "Data provider",
        "label_zh": "数据提供者",
        "typical_entity_types": ["dataset"],
    },
    "model_provider": {
        "label": "Model provider",
        "label_zh": "模型提供者",
        "typical_entity_types": ["llm"],
    },
    "witness": {
        "label": "Witness",
        "label_zh": "见证者",
        "typical_entity_types": ["llm", "community"],
        "advisory_only": True,
    },
    "verifier": {
        "label": "Verifier",
        "label_zh": "验证者",
        "typical_entity_types": ["llm", "agent"],
        "advisory_only": True,
    },
    "reviewer": {
        "label": "Reviewer",
        "label_zh": "审查者",
        "typical_entity_types": ["human", "agent", "llm", "skill", "organization", "community"],
        "final_authority": False,
    },
    "coordinator": {
        "label": "Coordinator",
        "label_zh": "协调者",
        "typical_entity_types": ["human", "agent", "workflow", "organization"],
    },
    "sponsor": {
        "label": "Sponsor",
        "label_zh": "赞助者",
        "typical_entity_types": ["organization", "community"],
    },
}

ACCOUNTABILITY_RULES = {
    "principle": "Finalization is policy-automated and traceable; all Entity types are equal network subjects.",
    "principle_zh": "终局由策略自动完成且可追溯；所有 Entity 类型是平等的网络主体。",
    "finalizer_entity_types": [
        "human",
        "agent",
        "llm",
        "skill",
        "tool",
        "dataset",
        "workflow",
        "compute_node",
        "verifier_node",
        "reviewer_node",
        "organization",
        "community",
        "sponsor",
        "protocol_treasury",
    ],
    "ai_advisory_entity_types": ["llm", "agent", "verifier_node"],
    "non_human_require_owner": [
        "agent",
        "skill",
        "tool",
        "dataset",
        "workflow",
        "compute_node",
        "verifier_node",
        "reviewer_node",
    ],
}

EXAMPLE_EVENT_TOPOLOGIES: list[dict[str, Any]] = [
    {
        "name": "study_notes_minimal",
        "description": "Pilot demo — R language study materials",
        "participants": [
            {"role": "creator", "entity_type": "human"},
            {"role": "executor", "entity_type": "agent"},
            {"role": "skill_provider", "entity_type": "skill"},
            {"role": "model_provider", "entity_type": "llm"},
            {"role": "witness", "entity_type": "llm"},
            {"role": "verifier", "entity_type": "llm"},
            {"role": "reviewer", "entity_type": "agent"},
            {"role": "sponsor", "entity_type": "organization"},
        ],
        "invocation_chain": ["human", "agent", "skill", "llm"],
    },
    {
        "name": "data_backed_report",
        "description": "Workflow + dataset + tool + multi-witness",
        "participants": [
            {"role": "creator", "entity_type": "human"},
            {"role": "coordinator", "entity_type": "workflow"},
            {"role": "executor", "entity_type": "agent"},
            {"role": "skill_provider", "entity_type": "skill"},
            {"role": "tool_provider", "entity_type": "tool"},
            {"role": "data_provider", "entity_type": "dataset"},
            {"role": "model_provider", "entity_type": "llm"},
            {"role": "verifier", "entity_type": "llm"},
            {"role": "reviewer", "entity_type": "agent"},
            {"role": "sponsor", "entity_type": "community"},
        ],
    },
]


def all_entity_types() -> list[str]:
    return list(ENTITY_TYPE_SPECS.keys())


def all_participant_roles() -> list[str]:
    return list(PARTICIPANT_ROLE_SPECS.keys())


def validate_entity_type(entity_type: str) -> None:
    if entity_type not in ENTITY_TYPE_SPECS:
        raise ValueError(f"Unknown entity_type: {entity_type}")


def validate_participant_role(role: str) -> None:
    if role not in PARTICIPANT_ROLE_SPECS:
        raise ValueError(f"Unknown participant role: {role}")


def role_fits_entity_type(role: str, entity_type: str) -> bool:
    spec = PARTICIPANT_ROLE_SPECS.get(role) or {}
    allowed = spec.get("typical_entity_types")
    if not allowed:
        return True
    return entity_type in allowed


def enrich_entity_record(entity: Any) -> dict[str, Any]:
    """Attach ontology slice to an Entity ORM object or dict."""
    et = entity.entity_type.value if hasattr(entity.entity_type, "value") else entity.get("entity_type")
    type_spec = ENTITY_TYPE_SPECS.get(et, {})
    meta = entity.metadata_ if hasattr(entity, "metadata_") else entity.get("metadata", {})
    return {
        "entity_id": entity.id if hasattr(entity, "id") else entity.get("id"),
        "entity_type": et,
        "name": entity.name if hasattr(entity, "name") else entity.get("name"),
        "status": entity.status.value if hasattr(entity.status, "value") else entity.get("status"),
        "ontology": {
            "type_spec": type_spec,
            "typical_roles": type_spec.get("typical_roles", []),
            "accountable_principal": type_spec.get("accountable_principal", False),
            "network_subject": type_spec.get("network_subject", True),
        },
        "metadata": meta or {},
        "compute_profile": meta.get("compute_profile") if meta else None,
    }


COMPUTE_CAPABILITIES = sorted(
    ["llm_inference", "embeddings", "witness", "mcp_host", "agent_runtime"]
)


def ontology_document() -> dict[str, Any]:
    return {
        "spec_version": "0.3",
        "principle": "Everything connects through verified contribution.",
        "principle_zh": "万物都有贡献，万物互联于贡献协议。",
        "entity_types": ENTITY_TYPE_SPECS,
        "participant_roles": PARTICIPANT_ROLE_SPECS,
        "accountability": ACCOUNTABILITY_RULES,
        "example_topologies": EXAMPLE_EVENT_TOPOLOGIES,
        "compute_capabilities": COMPUTE_CAPABILITIES,
        "compute_api": {
            "providers": "/api/v1/compute/providers",
            "register": "/api/v1/compute/entities/{entity_id}/register",
            "jobs": "/api/v1/compute/jobs",
            "research": "docs/DISTRIBUTED-COMPUTE-RESEARCH.md",
        },
        "docs": "docs/ENTITY-ONTOLOGY.md",
    }
