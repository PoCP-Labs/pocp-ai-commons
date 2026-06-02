"""Predefined mission handoff plans for Nexus-0 dispatch."""

from __future__ import annotations

from typing import TypedDict

from meta_agents_spec import NEXUS_ID

from services.agent_studio.handoffs import create_handoff, handoff_to_dict
from services.agent_studio.missions import activate_mission, create_mission, mission_to_dict


class HandoffPlanItem(TypedDict):
    from_agent_entity_id: str
    to_agent_entity_id: str
    scope: str
    tests_run: str


class MissionPlan(TypedDict):
    id: str
    title: str
    description: str
    kind: str
    handoffs: list[HandoffPlanItem]


PHASE_A_P0_PLAN: MissionPlan = {
    "id": "phase_a_p0",
    "title": "Phase A P0 — Exchange Spine + Wallet audit",
    "description": "Local optimization: federation exchange demo and wallet audit green.",
    "kind": "improve",
    "handoffs": [
        {
            "from_agent_entity_id": NEXUS_ID,
            "to_agent_entity_id": "pocp-agent-vault-0",
            "scope": "Exchange Spine + wallet audit: exchange_spine.py, wallet_*, GET /wallets/audit",
            "tests_run": "pytest -k 'exchange or wallet' && run_phase_a_acceptance.py",
        },
        {
            "from_agent_entity_id": NEXUS_ID,
            "to_agent_entity_id": "pocp-agent-mesh-0",
            "scope": "Federation exchange proof demo E2E; peer import policy checks",
            "tests_run": "pytest -k federation && run_phase_a_acceptance.py --federation",
        },
        {
            "from_agent_entity_id": "pocp-agent-vault-0",
            "to_agent_entity_id": "pocp-agent-gauge-0",
            "scope": "Verify wallet audit + exchange tests; report PASS/FAIL to Nexus",
            "tests_run": "pytest -k 'exchange or wallet'; run_phase_a_acceptance.py",
        },
        {
            "from_agent_entity_id": "pocp-agent-mesh-0",
            "to_agent_entity_id": "pocp-agent-gauge-0",
            "scope": "Verify federation acceptance including exchange proof demo",
            "tests_run": "run_phase_a_acceptance.py --federation",
        },
        {
            "from_agent_entity_id": "pocp-agent-gauge-0",
            "to_agent_entity_id": NEXUS_ID,
            "scope": "Consolidate Gauge report; gate merge on green acceptance",
            "tests_run": "full pytest + phase_a acceptance",
        },
        {
            "from_agent_entity_id": NEXUS_ID,
            "to_agent_entity_id": "pocp-agent-herald-0",
            "scope": "Sync LOCAL-SETUP and acceptance commands in docs after P0 green",
            "tests_run": "docs review",
        },
    ],
}

PHASE_A_FULL_PLAN: MissionPlan = {
    "id": "phase_a_full",
    "title": "Phase A — Full local optimization track",
    "description": "P0–P2: exchange, wallet, federation import, compute wire, frontend panels.",
    "kind": "evolve",
    "handoffs": [
        *PHASE_A_P0_PLAN["handoffs"],
        {
            "from_agent_entity_id": NEXUS_ID,
            "to_agent_entity_id": "pocp-agent-mesh-0",
            "scope": "P1: Federation L1 exchange import without silent BC mint",
            "tests_run": "federation import tests",
        },
        {
            "from_agent_entity_id": NEXUS_ID,
            "to_agent_entity_id": "pocp-agent-grid-0",
            "scope": "P1: Live compute adapter wire + documented config path",
            "tests_run": "pytest -k compute",
        },
        {
            "from_agent_entity_id": NEXUS_ID,
            "to_agent_entity_id": "pocp-agent-canvas-0",
            "scope": "P2: ProviderPanel + WalletPanel federation demo UX",
            "tests_run": "npm run build",
        },
        {
            "from_agent_entity_id": NEXUS_ID,
            "to_agent_entity_id": "pocp-agent-atlas-0",
            "scope": "Review schema/boundary for any P1 API changes",
            "tests_run": "protocol doc review",
        },
        {
            "from_agent_entity_id": NEXUS_ID,
            "to_agent_entity_id": "pocp-agent-lex-0",
            "scope": "Review README/UI for NO-TOKEN-FIRST compliance before pilot",
            "tests_run": "lex grep pass",
        },
    ],
}

PHASE_A_KERNEL_PLAN: MissionPlan = {
    "id": "phase_a_kernel",
    "title": "Phase A Kernel — Entity catalog + protocol integrity + federation gate",
    "description": (
        "PA-1..PA-6: 14 Entity types + capability registry, PR-A/B verify, "
        "federation acceptance green on :8100/:8101. See docs/agent-studio/PHASE-A-KERNEL-BACKLOG.md"
    ),
    "kind": "improve",
    "handoffs": [
        {
            "from_agent_entity_id": NEXUS_ID,
            "to_agent_entity_id": "pocp-agent-atlas-0",
            "scope": (
                "PA-1: Entity catalog — review entity_catalog.py + ontology; "
                "commit WIP; stable IDs for compute_node/verifier/reviewer/sponsor/treasury. "
                "Issue: docs/agent-studio/issues/PA-01-entity-catalog.md"
            ),
            "tests_run": "pytest backend/tests/test_entity_catalog.py -q",
        },
        {
            "from_agent_entity_id": "pocp-agent-atlas-0",
            "to_agent_entity_id": "pocp-agent-pulse-0",
            "scope": (
                "PA-1: Seed capability registry (11+ caps); wire seed.py startup; "
                "verify GET /registry/capabilities on Postgres not sqlite fallback."
            ),
            "tests_run": "python backend/scripts/audit_entities.py --repair",
        },
        {
            "from_agent_entity_id": NEXUS_ID,
            "to_agent_entity_id": "pocp-agent-vault-0",
            "scope": (
                "PA-2: Verify PR-A invocation_ref integrity — invocation_ledger.py, "
                "GET /exchanges/{id}/integrity. Issue: PA-02-invocation-integrity.md"
            ),
            "tests_run": "pytest -k invocation_ledger -q",
        },
        {
            "from_agent_entity_id": NEXUS_ID,
            "to_agent_entity_id": "pocp-agent-forge-0",
            "scope": (
                "PA-3: PR-B challenge/appeal + contribution_dispute; commit if pending. "
                "Issue: PA-03-settlement-challenge.md"
            ),
            "tests_run": "pytest -k 'verification_challenge or settlement_policy' -q",
        },
        {
            "from_agent_entity_id": "pocp-agent-forge-0",
            "to_agent_entity_id": "pocp-agent-prism-0",
            "scope": (
                "PA-3: Settlement policy tags on exchange_settled; replay API; "
                "settlement_policies.yaml alignment."
            ),
            "tests_run": "pytest backend/tests/test_settlement_policy_replay.py -q",
        },
        {
            "from_agent_entity_id": NEXUS_ID,
            "to_agent_entity_id": "pocp-agent-mesh-0",
            "scope": (
                "PA-4: Restart federation backends; full acceptance on :8100/:8101 NOT :8008. "
                "Issue: PA-04-federation-acceptance.md"
            ),
            "tests_run": (
                "docker compose -f docker-compose.federation.yml restart backend-a backend-b && "
                "python backend/scripts/run_phase_a_acceptance.py http://127.0.0.1:8100 "
                "--federation http://127.0.0.1:8101"
            ),
        },
        {
            "from_agent_entity_id": "pocp-agent-mesh-0",
            "to_agent_entity_id": "pocp-agent-gauge-0",
            "scope": (
                "PA-4 + PA-5: Gate on full pytest + federation acceptance; add entity_catalog "
                "acceptance step. Issues: PA-04, PA-05."
            ),
            "tests_run": "cd backend && python -m pytest -q",
        },
        {
            "from_agent_entity_id": "pocp-agent-gauge-0",
            "to_agent_entity_id": NEXUS_ID,
            "scope": "Consolidate kernel track Gauge report; mark mission complete when all PA green.",
            "tests_run": "run_phase_a_acceptance.py --federation + audit_entities.py --repair",
        },
        {
            "from_agent_entity_id": NEXUS_ID,
            "to_agent_entity_id": "pocp-agent-herald-0",
            "scope": "Update ROADMAP-THREE-PHASES.md + PHASE-A-KERNEL-BACKLOG status after kernel green.",
            "tests_run": "docs review",
        },
        {
            "from_agent_entity_id": NEXUS_ID,
            "to_agent_entity_id": "pocp-agent-sentinel-0",
            "scope": (
                "PA-6 backlog scaffold: reputation event-sourcing + MCP security baseline. "
                "Issue: PA-06-reputation-mcp-security.md — start only after PA-4 PASS."
            ),
            "tests_run": "spec + scaffold tests",
        },
    ],
}

PROTOCOL_LAYER_EDP_PLAN: MissionPlan = {
    "id": "protocol_layer_edp",
    "title": "Protocol Layer — Entity Dialogue Protocol (L2 native envelope)",
    "description": (
        "Decompose protocol-layer work into Issues PL-1..PL-10: EDP v0.1→v0.2, "
        "invoke→execute, quote/exchange, federation dialogue, proof refs, UI, docs. "
        "See agents/missions/protocol-layer-edp/MANIFEST.md"
    ),
    "kind": "evolve",
    "handoffs": [
        {
            "from_agent_entity_id": NEXUS_ID,
            "to_agent_entity_id": "pocp-agent-atlas-0",
            "scope": (
                "[PL-1 Issue] EDP v0.1 spec audit: ENTITY-DIALOGUE-PROTOCOL.md vs "
                "ENTITY-CONNECTION + TRUST-POLICY-BUNDLE; fix gaps; draft v0.2 quote/federation_accept."
            ),
            "tests_run": "protocol doc review + pytest test_entity_dialogue -q",
        },
        {
            "from_agent_entity_id": "pocp-agent-atlas-0",
            "to_agent_entity_id": "pocp-agent-pulse-0",
            "scope": (
                "[PL-2 Issue] Wire dialogue invoke kind to metered capability_execute "
                "(execute_skill/execute_agent) with CapabilityReceipt — not trace-only."
            ),
            "tests_run": "pytest test_entity_dialogue test_capability_execute -q",
        },
        {
            "from_agent_entity_id": NEXUS_ID,
            "to_agent_entity_id": "pocp-agent-vault-0",
            "scope": (
                "[PL-3 Issue] Implement quote dialogue kind + exchange intent binding "
                "(exchange_spine quote → invoke chain)."
            ),
            "tests_run": "pytest test_exchange_spine test_entity_dialogue -q",
        },
        {
            "from_agent_entity_id": NEXUS_ID,
            "to_agent_entity_id": "pocp-agent-mesh-0",
            "scope": (
                "[PL-4 Issue] federation_accept handler + peer dialogue routing doc; "
                "validate-proof via dialogue envelope on import path."
            ),
            "tests_run": "pytest test_federation test_entity_dialogue test_trust_policy_bundle -q",
        },
        {
            "from_agent_entity_id": "pocp-agent-atlas-0",
            "to_agent_entity_id": "pocp-agent-pulse-0",
            "scope": (
                "[PL-5 Issue] REST/A2A → dialogue binding map (docs/protocol/BINDING-TO-DIALOGUE.md); "
                "A2A SendMessage deferred binding to submit kind."
            ),
            "tests_run": "pytest test_a2a_task_bridge -q",
        },
        {
            "from_agent_entity_id": NEXUS_ID,
            "to_agent_entity_id": "pocp-agent-vault-0",
            "scope": (
                "[PL-6 Issue] Proof packet export includes dialogue_id refs from "
                "InvocationStep metadata in proof.py."
            ),
            "tests_run": "pytest test_pow_export test_protocol_layer -q",
        },
        {
            "from_agent_entity_id": NEXUS_ID,
            "to_agent_entity_id": "pocp-agent-canvas-0",
            "scope": (
                "[PL-7 Issue] Entity Dialogue panel on EntityDetail — ping/discover/invoke "
                "forms calling POST .../entities/{id}/dialogue."
            ),
            "tests_run": "npm run build",
        },
        {
            "from_agent_entity_id": NEXUS_ID,
            "to_agent_entity_id": "pocp-agent-herald-0",
            "scope": (
                "[PL-8 Issue] LOCAL-SETUP + docs/protocol/README dialogue API examples; "
                "link ENTITY-DIALOGUE-PROTOCOL in onboarding path."
            ),
            "tests_run": "docs review",
        },
        {
            "from_agent_entity_id": NEXUS_ID,
            "to_agent_entity_id": "pocp-agent-gauge-0",
            "scope": (
                "[PL-9 Issue] Protocol layer acceptance: test_entity_dialogue + entity_connections + "
                "trust_policy + protocol_layer green; report PASS/FAIL."
            ),
            "tests_run": "pytest test_entity_dialogue test_entity_connections test_trust_policy_bundle test_protocol_layer -q",
        },
        {
            "from_agent_entity_id": "pocp-agent-gauge-0",
            "to_agent_entity_id": NEXUS_ID,
            "scope": (
                "[PL-10 Issue] Nexus consolidate protocol_layer_edp mission; close when all PL PAs green."
            ),
            "tests_run": "full protocol pytest suite",
        },
    ],
}

MISSION_PLANS: dict[str, MissionPlan] = {
    PHASE_A_P0_PLAN["id"]: PHASE_A_P0_PLAN,
    PHASE_A_KERNEL_PLAN["id"]: PHASE_A_KERNEL_PLAN,
    PHASE_A_FULL_PLAN["id"]: PHASE_A_FULL_PLAN,
    PROTOCOL_LAYER_EDP_PLAN["id"]: PROTOCOL_LAYER_EDP_PLAN,
}


def list_mission_plans() -> list[dict]:
    return [
        {
            "id": p["id"],
            "title": p["title"],
            "description": p["description"],
            "kind": p["kind"],
            "handoff_count": len(p["handoffs"]),
        }
        for p in MISSION_PLANS.values()
    ]


def spawn_plan_handoffs(db, mission_id: str, plan_id: str) -> list[dict]:
    plan = MISSION_PLANS.get(plan_id)
    if plan is None:
        raise ValueError(f"Unknown plan_id: {plan_id}. Available: {list(MISSION_PLANS)}")
    created = []
    for item in plan["handoffs"]:
        handoff = create_handoff(
            db,
            from_agent_entity_id=item["from_agent_entity_id"],
            to_agent_entity_id=item["to_agent_entity_id"],
            mission_id=mission_id,
            scope=item["scope"],
            tests_run=item.get("tests_run"),
        )
        created.append(handoff_to_dict(handoff))
    return created


def create_mission_from_plan(
    db,
    plan_id: str,
    *,
    title_override: str | None = None,
    sponsor_entity_id: str | None = None,
    activate: bool = True,
    spawn_handoffs: bool = True,
) -> dict:
    plan = MISSION_PLANS.get(plan_id)
    if plan is None:
        raise ValueError(f"Unknown plan_id: {plan_id}")
    mission = create_mission(
        db,
        title=title_override or plan["title"],
        description=plan["description"],
        kind=plan["kind"],
        sponsor_entity_id=sponsor_entity_id,
    )
    if activate:
        activate_mission(db, mission.id)
    handoffs: list[dict] = []
    if spawn_handoffs:
        handoffs = spawn_plan_handoffs(db, mission.id, plan_id)
    return {
        "mission": mission_to_dict(mission),
        "plan_id": plan_id,
        "handoffs": handoffs,
        "handoff_count": len(handoffs),
    }
