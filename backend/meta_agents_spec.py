"""Canonical Meta Agent definitions for PoCP engineering orchestration."""

from __future__ import annotations

from typing import Any, TypedDict

NEXUS_ID = "pocp-agent-nexus-0"
META_AGENT_LAYER = "meta_orchestration"
META_AGENT_PROJECT = "PoCP AI Commons"
META_AGENT_CREATED_BY = "PoCP-Labs"


class MetaAgentSpecDict(TypedDict):
    id: str
    slug: str
    name: str
    task_label: str
    description: str
    roles: list[str]
    capabilities: list[str]
    writable_paths: list[str]
    reports_to: str | None
    handoff_default: str
    orchestrates: list[str]


def _spec(
    slug: str,
    name: str,
    task_label: str,
    description: str,
    roles: list[str],
    capabilities: list[str],
    writable_paths: list[str],
    *,
    reports_to: str | None = NEXUS_ID,
    orchestrates: list[str] | None = None,
) -> MetaAgentSpecDict:
    agent_id = f"pocp-agent-{slug}"
    return {
        "id": agent_id,
        "slug": slug,
        "name": name,
        "task_label": task_label,
        "description": description,
        "roles": roles,
        "capabilities": capabilities,
        "writable_paths": writable_paths,
        "reports_to": None if slug == "nexus-0" else reports_to,
        "handoff_default": NEXUS_ID,
        "orchestrates": orchestrates or [],
    }


META_AGENT_SPECS: list[MetaAgentSpecDict] = [
    _spec(
        "nexus-0",
        "Nexus-0",
        "pocp-nexus",
        (
            "Autonomous project manager — decomposes roadmap goals, dispatches Meta Agents, "
            "monitors handoffs, advances missions without waiting for human task lists."
        ),
        roles=["autonomous_pm", "orchestrator", "tech_lead", "sprint_integrator"],
        capabilities=[
            "goal_decomposition",
            "autopilot_dispatch",
            "progress_review",
            "broad_research",
            "self_learning",
            "agent_coaching",
            "skill_training",
            "task_routing",
            "pr_slicing",
            "conflict_resolution",
            "acceptance_gating",
            "agent_mobilization",
        ],
        writable_paths=[
            "agents/**",
            "docs/ROADMAP-THREE-PHASES.md",
            ".github/pull_request_template.md",
            ".github/ISSUE_TEMPLATE/**",
            "README.md",
        ],
        reports_to=None,
        orchestrates=[f"pocp-agent-{s}" for s in (
            "atlas-0", "forge-0", "vault-0", "mesh-0", "pulse-0", "grid-0", "prism-0",
            "canvas-0", "sentinel-0", "gauge-0", "pipeline-0", "compass-0", "lex-0", "herald-0",
        )],
    ),
    _spec(
        "atlas-0",
        "Atlas-0",
        "pocp-atlas",
        "Protocol architect — Entity-Centric schemas, Open Core boundaries, module design.",
        roles=["protocol_architect", "schema_guardian"],
        capabilities=["schema_review", "open_core_boundary", "api_contract_freeze"],
        writable_paths=[
            "docs/protocol/**",
            "docs/architecture/**",
            "docs/PROTOCOL.md",
            "docs/ARCHITECTURE.md",
            "docs/ENTITY-*.md",
            "NEURAL-COMMONS-*.md",
            "backend/services/*/base.py",
            "backend/services/*/schemas.py",
        ],
    ),
    _spec(
        "forge-0",
        "Forge-0",
        "pocp-forge",
        "Contribution & verification — submit, evidence, multi-verifier advisory, finalization.",
        roles=["contribution_engineer", "verifier_integrator"],
        capabilities=["contribution_submit", "multi_verifier", "finalization_trace", "evidence_validation"],
        writable_paths=[
            "backend/services/contribution*.py",
            "backend/services/finalization.py",
            "backend/services/evidence*.py",
            "backend/services/verifiers/**",
            "backend/services/clarion.py",
            "backend/routers/verification.py",
            "backend/tests/**/test_contribution*",
            "backend/tests/**/test_verif*",
        ],
    ),
    _spec(
        "vault-0",
        "Vault-0",
        "pocp-vault",
        "Proof, ledger & wallet — hash chain, portable proofs, exchange spine, audit.",
        roles=["ledger_engineer", "proof_engineer", "wallet_engineer"],
        capabilities=["proof_packet", "ledger_chain", "wallet_audit", "exchange_spine"],
        writable_paths=[
            "backend/services/proof.py",
            "backend/services/ledger_*.py",
            "backend/services/graph*.py",
            "backend/services/wallet_*.py",
            "backend/services/exchange_spine.py",
            "backend/routers/export.py",
            "backend/routers/wallet.py",
            "backend/tests/**/test_proof*",
            "backend/tests/**/test_wallet*",
        ],
    ),
    _spec(
        "mesh-0",
        "Mesh-0",
        "pocp-mesh",
        "Federation & portability — multi-node peers, proof import, remote witness.",
        roles=["federation_engineer", "distributed_systems"],
        capabilities=["federation_peers", "portable_entity", "exchange_import", "acceptance_federation"],
        writable_paths=[
            "backend/services/federation_*.py",
            "backend/services/entity_portable.py",
            "backend/routers/federation.py",
            "backend/scripts/run_phase_a_acceptance.py",
            "scripts/run-phase-a.*",
            "docs/FEDERATION*.md",
        ],
    ),
    _spec(
        "pulse-0",
        "Pulse-0",
        "pocp-pulse",
        "Capability & invocation — MCP, skill calls, rule-based neural routing.",
        roles=["capability_engineer", "mcp_integrator"],
        capabilities=["capability_execute", "mcp_invoke", "invocation_ledger", "neural_routing"],
        writable_paths=[
            "backend/services/capability/**",
            "backend/services/neural/**",
            "backend/services/mcp_*.py",
            "backend/services/invocation*.py",
            "backend/intelligence/**",
            "backend/routers/capabilities.py",
            "backend/routers/intelligence.py",
        ],
    ),
    _spec(
        "grid-0",
        "Grid-0",
        "pocp-grid",
        "Compute mesh — adapters, scheduling, utilization receipts in proof.",
        roles=["compute_platform_engineer"],
        capabilities=["compute_adapters", "compute_jobs", "compute_receipt", "peer_compute"],
        writable_paths=[
            "backend/services/compute/**",
            "backend/services/compute_*.py",
            "backend/routers/compute.py",
            "docs/COMPUTE*.md",
        ],
    ),
    _spec(
        "prism-0",
        "Prism-0",
        "pocp-prism",
        "Token measurement & settlement — CP, AIC, CC internal accounting and splits.",
        roles=["settlement_engineer", "measurement_engineer"],
        capabilities=["token_measurement", "settlement_policy", "reputation_measurement"],
        writable_paths=[
            "backend/services/token_measurement/**",
            "backend/services/settlement/**",
            "backend/services/settlement_*.py",
            "docs/protocol/TOKEN-MEASUREMENT-*.md",
            "docs/protocol/SETTLEMENT-*.md",
        ],
    ),
    _spec(
        "canvas-0",
        "Canvas-0",
        "pocp-canvas",
        "Frontend & UX — dashboard, wallet, graph, proof verify, task flows.",
        roles=["frontend_engineer", "ux_implementer"],
        capabilities=["react_dashboard", "proof_deep_link", "wallet_panel", "graph_explorer"],
        writable_paths=["frontend/**", "docs/implementation/FRONTEND-MODULE-PLAN.md"],
    ),
    _spec(
        "sentinel-0",
        "Sentinel-0",
        "pocp-sentinel",
        "Security & open-core anti-abuse — auth, export, federation threat review.",
        roles=["security_engineer", "abuse_prevention"],
        capabilities=["anti_abuse", "crypto_suite", "security_audit", "evidence_validate"],
        writable_paths=[
            "backend/services/anti_abuse.py",
            "backend/services/crypto_suite.py",
            "backend/services/evidence_validate.py",
            "backend/routers/auth.py",
            "backend/tests/**/test_anti_abuse*",
        ],
    ),
    _spec(
        "gauge-0",
        "Gauge-0",
        "pocp-gauge",
        "QA & acceptance — pytest, phase-a runner, federation E2E.",
        roles=["qa_engineer", "acceptance_owner"],
        capabilities=["pytest", "phase_a_acceptance", "federation_ci", "regression_tests"],
        writable_paths=[
            "backend/tests/**",
            "backend/scripts/run_phase_a_acceptance.py",
            ".github/workflows/smoke-test.yml",
            ".github/workflows/phase-a-federation.yml",
            "scripts/run-phase-a.*",
        ],
    ),
    _spec(
        "pipeline-0",
        "Pipeline-0",
        "pocp-pipeline",
        "CI/CD & environments — workflows, staging templates, no secrets in git.",
        roles=["devops_engineer", "sre"],
        capabilities=["github_actions", "staging_scripts", "env_templates"],
        writable_paths=[
            ".github/workflows/**",
            "scripts/**",
            "backend/.env.staging.example",
            "docs/LOCAL-SETUP.md",
        ],
    ),
    _spec(
        "compass-0",
        "Compass-0",
        "pocp-compass",
        "Product & roadmap — priorities, acceptance criteria, pilot scope.",
        roles=["product_manager", "roadmap_owner"],
        capabilities=["roadmap_planning", "issue_triage", "pilot_metrics"],
        writable_paths=[
            "docs/ROADMAP-THREE-PHASES.md",
            "docs/PILOT-LAUNCH-CHECKLIST.md",
            "docs/VISION.md",
            ".github/ISSUE_TEMPLATE/**",
            "agents/**",
        ],
    ),
    _spec(
        "lex-0",
        "Lex-0",
        "pocp-lex",
        "Compliance & public language — NO-TOKEN-FIRST, economic copy review.",
        roles=["compliance_reviewer", "public_language"],
        capabilities=["no_token_first_review", "economic_copy_veto", "pilot_messaging"],
        writable_paths=[
            "NO-TOKEN-FIRST.md",
            "README.md",
            "docs/ACCOUNTABILITY-BOUNDARY.md",
            "docs/genesis/**",
            ".github/ISSUE_TEMPLATE/**",
        ],
    ),
    _spec(
        "herald-0",
        "Herald-0",
        "pocp-herald",
        "Documentation & DevRel — onboarding, protocol docs, third-party node guides.",
        roles=["technical_writer", "devrel"],
        capabilities=["onboarding_docs", "protocol_sync", "issue_templates"],
        writable_paths=[
            "docs/**",
            "README.md",
            "README-NEURAL-COMMONS.md",
            "CONTRIBUTOR*.md",
            ".github/ISSUE_TEMPLATE/**",
            "agents/**",
        ],
    ),
]

META_AGENT_IDS: frozenset[str] = frozenset(s["id"] for s in META_AGENT_SPECS)
META_AGENT_BY_ID: dict[str, MetaAgentSpecDict] = {s["id"]: s for s in META_AGENT_SPECS}


def agent_config_for_spec(spec: MetaAgentSpecDict) -> dict[str, Any]:
    slug = spec["slug"]
    mem_slug = "_studio" if slug == "nexus-0" else slug
    return {
        "meta_agent": True,
        "layer": META_AGENT_LAYER,
        "slug": slug,
        "task_label": spec["task_label"],
        "role": spec["roles"][0],
        "capabilities": spec["capabilities"],
        "memory_store": {
            "path": f"data/agent_studio/memory/{mem_slug}",
            "max_entries": 500,
            "sync_files": True,
        },
        "learning_profile": {
            "evolution_version": 0,
            "strengths": [],
            "growth_areas": [],
            "evolved_capabilities": [],
            "memory_store_path": f"data/agent_studio/memory/{mem_slug}",
        },
        "writable_paths": spec["writable_paths"],
        "reports_to": spec["reports_to"],
        "handoff_default": spec["handoff_default"],
        "orchestrates": spec["orchestrates"],
        "prompt_path": f"agents/prompts/{slug}.md",
        "cursor_rule": f".cursor/rules/pocp-{slug}.mdc",
        "cursor_skill": f".cursor/skills/pocp-{slug.replace('-0', '')}/SKILL.md",
        "roster_path": "agents/ROSTER.md",
        "global_rules_path": "agents/prompts/_global.md",
        "decision_boundary": "engineering_only_no_rights_finalization",
        "governance_note": (
            "Meta Agent builds the platform; does not finalize CP/AI Credits on live contributions. "
            "Runtime witnesses (Lumen-0, DeSui, Clarion-0) handle protocol verification."
        ),
    }


def entity_metadata_for_spec(spec: MetaAgentSpecDict) -> dict[str, Any]:
    return {
        "meta_agent": True,
        "layer": META_AGENT_LAYER,
        "slug": spec["slug"],
        "task_label": spec["task_label"],
        "roles": spec["roles"],
        "capabilities": spec["capabilities"],
        "project": META_AGENT_PROJECT,
        "created_by": META_AGENT_CREATED_BY,
        "reports_to": spec["reports_to"],
        "handoff_default": spec["handoff_default"],
        "prompt_path": f"agents/prompts/{spec['slug']}.md",
        "cursor_skill": agent_config_for_spec(spec)["cursor_skill"],
        "governance_note": agent_config_for_spec(spec)["governance_note"],
    }
