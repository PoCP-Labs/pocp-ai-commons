# Nexus Research — doc sync report (Herald-0)

**Handoff:** `1d0e761b-d0dd-4563-9440-74ee63ad46f2`  
**Mission:** `84895eb8-119b-45b0-b56c-3173b69fc4c3`  
**Agent:** `pocp-agent-herald-0`  
**Generated:** 2026-06-03

## Handoff — Herald-0

- **Scope:** `[Nexus Research]` Sync roadmap/protocol review findings into `docs/` and onboarding; report gaps to Nexus-0.
- **Files:**
  - `docs/LOCAL-SETUP.md` — CIP minimum living network onboarding (was missing despite prior cycle claim)
  - `README.md` — Development Status P2 CIP skeleton row (align with ROADMAP-THREE-PHASES)
  - `docs/ROADMAP-THREE-PHASES.md` — tracking row → this report
  - `agents/patches/nexus-research-gaps-1d0e761b.md` — this report
- **Tests run:** docs review + README consistency; `pytest tests/test_meta_agent_registry.py`; `ensure_meta_agents.py`; `health_check.py`; `minimum_living_network.py`; issue-template Phase/CIP grep
- **Result:** pass
- **Blockers:** none for Herald writable paths
- **Skill gaps:** none
- **Next agent:** Atlas-0 (CIP layer spec vs OpenAPI); Gauge-0 (wire CIP demo into CI after P0 green); Forge-0 (PR 4 runtime APIs)

## Sync completed this cycle

| Area | Action |
|------|--------|
| Onboarding gap fix | `LOCAL-SETUP.md` — `minimum_living_network.py` + spec/mission links under Phase A section |
| README ↔ ROADMAP | Development Status table — **P2 CIP skeleton** row matches [ROADMAP-THREE-PHASES.md](../../docs/ROADMAP-THREE-PHASES.md) § Local optimization |
| Nexus queue context | Incorporated [compass-0-reconcile-a7f1b08d.md](./compass-0-reconcile-a7f1b08d.md): CIP is **P2 parallel** to EDP; does not preempt Exchange Spine **P0** |

## Already aligned (no edit required)

| Area | Status |
|------|--------|
| CIP 12-layer index | [docs/protocol/README.md](../../docs/protocol/README.md) |
| Docs index | [docs/README.md](../../docs/README.md) § Capability Internet Protocol |
| Architecture layer map | [docs/POCP-NETWORK-ARCHITECTURE.md](../../docs/POCP-NETWORK-ARCHITECTURE.md) |
| Contributor guide | [CONTRIBUTOR-QUALITY-GUIDE.md](../../CONTRIBUTOR-QUALITY-GUIDE.md) — CIP demo command |
| Issue templates | `cip_runtime_task.md`, `capability_internet_protocol_task.md` — Phase + `--federation` acceptance |
| Implementation checklists | MINIMUM-LIVING-NETWORK-DEMO, CURSOR-CAPABILITY-INTERNET-EXECUTION |
| In-memory demo | `backend/scripts/minimum_living_network.py` — **green** this cycle |

## Gaps remaining (for Nexus / domain agents)

| Priority | Gap | Suggested owner |
|----------|-----|-----------------|
| **P0** | Exchange Spine + Wallet federation acceptance (blocks staging) | Vault-0, Mesh-0, Gauge-0 |
| **P1** | CIP demo not in CI (`minimum_living_network.py`) | Gauge-0 + Pipeline-0 — **after** P0 green per Compass reconcile |
| **P1** | CIP skeleton not wired to production APIs (PR 4 in STAGED-PR-PLAN) | Forge-0, Pulse-0 |
| **P2** | Genesis translations (zh-CN / de) Phase C sync not audited | Herald-0 on release milestone |
| **P2** | CIP layer specs not auto-validated against OpenAPI on schema changes | Atlas-0 + Gauge-0 |
| **P2** | `P2P-NETWORK-SPEC.md` still missing (Phase B) | Atlas-0, Mesh-0 |
| **P3** | Legacy [ROADMAP.md](../../ROADMAP.md) deprecation banner | Compass-0 |
| **P3** | `INTELLECTUAL-EQUALITY.md` referenced in pilot recruit doc but missing | Atlas-0 / Lex-0 |

## Nexus operational notes

1. **Meta queue bloat** — Compass reports 133+ open Training/Review/Research handoffs; prioritize Vault/Mesh/Gauge P0 before spawning duplicate Herald Research handoffs.
2. **Duplicate handoffs** — Mark `e2131c5b` and prior Herald Research cycles completed when closing `1d0e761b`.
3. **Branch `capability-internet-protocol`** — CIP backend `.bak` pairs in git status are Forge/Atlas territory; Herald only documents shipped paths under `docs/` and onboarding commands.

## Nexus research corpus alignment

No new `RESEARCH_CORPUS` paths. CIP mission + 12-layer specs indexed from `docs/README.md` and `docs/protocol/README.md`. ROADMAP P2 CIP row now mirrored in root README Development Status.
