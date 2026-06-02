"""Platform capability registry seeds — stable IDs for Phase A kernel (PA-1)."""

from __future__ import annotations

from typing import Any

from genesis import CLARION_0_ID, DESUI_ID, LUMEN_0_ID

# Infrastructure entity IDs (must exist before capability rows register).
LOCAL_COMPUTE_NODE_ID = "pocp-entity-local-compute"
LOCAL_VERIFIER_NODE_ID = "pocp-entity-local-verifier"
BOB_REVIEWER_NODE_ID = "pocp-entity-bob-reviewer"
RAIN_SPONSOR_ID = "pocp-entity-rain-sponsor"
PROTOCOL_TREASURY_ID = "pocp-entity-protocol-treasury"
R_DOCS_TOOL_ID = "pocp-entity-r-docs-tool"
STUDY_WORKFLOW_ID = "pocp-entity-study-workflow"

SKILL_CAPABILITY_ID = "pocp-cap-r-tutor-coding"
REGISTRY_MIN_COUNT = 11

CAPABILITY_SEEDS: list[dict[str, Any]] = [
    {
        "capability_id": "pocp-cap-lumen-reasoning",
        "entity_id": LUMEN_0_ID,
        "capability_type": "reasoning",
        "name": "Advisory reasoning",
        "unit": "llm_token",
        "verification_method": "ai_review",
        "metadata": {"model": "Lumen-0", "layer": "genesis"},
    },
    {
        "capability_id": "pocp-cap-lumen-review",
        "entity_id": LUMEN_0_ID,
        "capability_type": "review",
        "name": "Witness interpretation",
        "unit": "task",
        "verification_method": "ai_review",
        "metadata": {"role": "witness"},
    },
    {
        "capability_id": "pocp-cap-desui-verification",
        "entity_id": DESUI_ID,
        "capability_type": "verification",
        "name": "Adversarial verification",
        "unit": "task",
        "verification_method": "ai_review",
        "metadata": {"role": "verifier"},
    },
    {
        "capability_id": "pocp-cap-clarion-review",
        "entity_id": CLARION_0_ID,
        "capability_type": "review",
        "name": "Contribution evidence structuring",
        "unit": "task",
        "verification_method": "human_review",
        "metadata": {"decision_boundary": "advisory_only"},
    },
    {
        "capability_id": "pocp-cap-local-compute-gpu",
        "entity_id": LOCAL_COMPUTE_NODE_ID,
        "capability_type": "gpu_inference",
        "name": "Local GPU/CPU inference",
        "unit": "gpu_second",
        "base_price": 1.0,
        "accepted_units": ["AIC", "CC"],
        "verification_method": "log",
        "metadata": {"adapters": ["ollama", "llama_cpp", "mock"]},
    },
    {
        "capability_id": "pocp-cap-local-verifier",
        "entity_id": LOCAL_VERIFIER_NODE_ID,
        "capability_type": "verification",
        "name": "Hybrid witness verification",
        "unit": "task",
        "verification_method": "peer_witness",
        "metadata": {"kinds": ["ai_review", "peer_witness"]},
    },
    {
        "capability_id": "pocp-cap-r-docs-tool",
        "entity_id": R_DOCS_TOOL_ID,
        "capability_type": "tool_call",
        "name": "R documentation lookup",
        "unit": "skill_invocation",
        "verification_method": "log",
        "metadata": {"mcp_server": "r-docs"},
    },
    {
        "capability_id": "pocp-cap-rain-sponsor",
        "entity_id": RAIN_SPONSOR_ID,
        "capability_type": "governance",
        "name": "Task bounty sponsorship",
        "unit": "task",
        "price_model": "sponsored",
        "verification_method": "human_review",
        "metadata": {"sponsor_policy": "task_bounty"},
    },
    {
        "capability_id": "pocp-cap-bob-reviewer",
        "entity_id": BOB_REVIEWER_NODE_ID,
        "capability_type": "review",
        "name": "Human governance review",
        "unit": "task",
        "verification_method": "human_review",
        "metadata": {"review_policy": "governance_proxy"},
    },
    {
        "capability_id": "pocp-cap-protocol-treasury",
        "entity_id": PROTOCOL_TREASURY_ID,
        "capability_type": "governance",
        "name": "Protocol fee reserve",
        "unit": "task",
        "price_model": "fixed",
        "verification_method": "log",
        "metadata": {"treasury_policy": "protocol_reserve"},
    },
]


def expected_capability_ids(*, include_skill: bool = True) -> list[str]:
    """Stable capability IDs used for PA-1 audit completeness."""
    ids = [spec["capability_id"] for spec in CAPABILITY_SEEDS]
    if include_skill:
        ids.append(SKILL_CAPABILITY_ID)
    return ids
