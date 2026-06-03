# Nexus Research — doc sync report (Herald-0)

**Handoff:** `e2131c5b-4036-44c5-a847-1696a20afeac`  
**Mission:** none  
**Agent:** `pocp-agent-herald-0`  
**Generated:** 2026-06-02

## Handoff — Herald-0

- **Scope:** `[Nexus Research]` Sync roadmap/protocol review findings into `docs/` and onboarding; report gaps to Nexus-0.
- **Files:**
  - `docs/protocol/README.md` — CIP 12-layer spec index + demo command
  - `docs/README.md` — Capability Internet Protocol section
  - `docs/POCP-NETWORK-ARCHITECTURE.md` — layer table links CIP specs + `backend/services/cip/` skeleton
  - `docs/LOCAL-SETUP.md` — CIP minimum living network onboarding
  - `docs/MINIMUM-LIVING-NETWORK.md` — CIP demo command
  - `docs/ROADMAP-THREE-PHASES.md` — P2 CIP skeleton track + tracking rows
  - `docs/implementation/MINIMUM-LIVING-NETWORK-DEMO.md` — expanded demo checklist
  - `docs/implementation/CURSOR-CAPABILITY-INTERNET-EXECUTION.md` — expanded execution checklist
  - `README.md` — CIP docs links + Development Status P2 row
  - `CONTRIBUTOR-QUALITY-GUIDE.md` — CIP demo verification
  - `.github/ISSUE_TEMPLATE/cip_runtime_task.md` — Phase & verification block
  - `agents/patches/nexus-research-gaps-e2131c5b.md` — this report
- **Tests run:** `pytest tests/test_meta_agent_registry.py`; `ensure_meta_agents.py`; `health_check.py`; `minimum_living_network.py`; issue-template Phase coverage grep; README link spot-check
- **Result:** pass
- **Blockers:** none for Herald writable paths
- **Next agent:** Atlas-0 (CIP layer spec audit vs OpenAPI); Gauge-0 (wire CIP demo into CI); Forge-0 (PR 4 runtime APIs)

## Sync completed this cycle

| Area | Action |
|------|--------|
| CIP layer specs | Indexed 12-layer specs in `docs/protocol/README.md` (ENTITY-LAYER through PROTOCOL-ECONOMY + CAPABILITY-SCHEMA) |
| Architecture status | `POCP-NETWORK-ARCHITECTURE.md` — CIP specs + `backend/services/cip/` skeleton in layer table |
| Onboarding | LOCAL-SETUP + CONTRIBUTOR-QUALITY-GUIDE — `minimum_living_network.py` command |
| Roadmap alignment | ROADMAP-THREE-PHASES + README Development Status — P2 CIP skeleton (parallel to EDP, does not preempt Exchange Spine P0) |
| Implementation docs | Expanded MINIMUM-LIVING-NETWORK-DEMO + CURSOR-CAPABILITY-INTERNET-EXECUTION |
| Issue template | `cip_runtime_task.md` — Phase & verification with CIP demo + federation acceptance |
| Docs index | `docs/README.md` — Capability Internet Protocol section |

## Prior cycles (already landed)

See `agents/patches/nexus-research-gaps-f1e009ff.md`, `9a9e9811.md`, `be66c695.md` — ENTITY-EQUALITY, Meta Agents, EDP track, issue template Phase blocks, local optimization P0.

## Gaps remaining (for Nexus / domain agents)

| Priority | Gap | Suggested owner |
|----------|-----|-----------------|
| **P1** | CIP demo not in CI (`minimum_living_network.py`) | Gauge-0 + Pipeline-0 |
| **P1** | CIP skeleton not wired to production APIs (PR 4 in STAGED-PR-PLAN) | Forge-0, Pulse-0 |
| **P2** | Genesis translations (zh-CN / de) Phase C sync not audited | Herald-0 on release milestone |
| **P2** | CIP layer specs not auto-validated against OpenAPI on schema changes | Atlas-0 + Gauge-0 |
| **P2** | `P2P-NETWORK-SPEC.md` still missing (Phase B) | Atlas-0, Mesh-0 |
| **P3** | Legacy [ROADMAP.md](../../ROADMAP.md) deprecation banner | Compass-0 |
| **P3** | `INTELLECTUAL-EQUALITY.md` referenced in pilot recruit doc but missing | Atlas-0 / Lex-0 |

## Nexus research corpus alignment

No new `RESEARCH_CORPUS` paths — CIP mission manifest and layer specs now indexed from `docs/README.md` and `docs/protocol/README.md`.
