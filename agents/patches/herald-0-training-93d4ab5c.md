# Nexus Training — Herald-0 coach cycle report

**Handoff:** `93d4ab5c-4516-4c1e-a86a-0cd55c977c3c`  
**Mission:** `fa62e623-a98e-464e-b6e7-3f4ab95e992d`  
**Agent:** `pocp-agent-herald-0`  
**Generated:** 2026-06-01

## Handoff — Herald-0

- **Scope:** `[Nexus Training]` Coach cycle — study `agents/prompts/herald-0.md`, run `pocp-herald` roster tests, report blockers + skill gaps. Capabilities: `onboarding_docs`, `protocol_sync`, `issue_templates`.
- **Files:**
  - `agents/prompts/herald-0.md` — Nexus Training duty, handoff template, `pocp-herald` verification commands
  - `README.md` — Development Status local P0 table; protocol v0.4 index link
  - `docs/LOCAL-SETUP.md` — CURSOR-AUTOMATION onboarding link
  - `.github/ISSUE_TEMPLATE/code_contribution_task.md` — Phase + verification table
  - `.github/ISSUE_TEMPLATE/test_task.md` — Phase + verification table
  - `.github/ISSUE_TEMPLATE/good_first_contribution.md` — Phase + verification table
  - `.github/ISSUE_TEMPLATE/bug_report.md` — regression verification table
  - `.github/ISSUE_TEMPLATE/feature_request.md` — Phase + verification table
  - `agents/patches/herald-0-training-93d4ab5c.md` — this report
- **Tests run:** see below
- **Result:** pass (registry + health_check)
- **Blockers:** none for Herald writable paths
- **Skill gaps:** see below
- **Next agent:** Compass-0 (legacy ROADMAP deprecation banner), Atlas-0 (ENTITY-EQUALITY vs CONSTITUTION review), Pipeline-0 (CURSOR-AUTOMATION CI worker docs)

## Tests run

| Command | Purpose |
|---------|---------|
| `cd backend && python -m pytest -q tests/test_meta_agent_registry.py` | Roster includes Herald-0; registry upsert |
| `python backend/scripts/ensure_meta_agents.py` | Idempotent meta-agent upsert |
| `python backend/scripts/health_check.py` | README / doc link sanity |

## Gaps closed this cycle

| Priority | Gap | Action |
|----------|-----|--------|
| **P1** | Issue templates lack verification commands | Updated 5 core templates (+ pilot/issue_spec from prior cycle) |
| **P1** | README Development Status vs local P0 | Added local optimization table from ROADMAP-THREE-PHASES |
| **P2** | Protocol v0.4 not cross-linked from README | Added `docs/protocol/README.md` to Genesis Package table |
| **P2** | CURSOR-AUTOMATION not in LOCAL-SETUP path | Linked from Meta Agents section |

## Gaps remaining (for Nexus / domain agents)

| Priority | Gap | Suggested owner |
|----------|-----|-----------------|
| **P2** | Genesis translations (zh-CN / de) Phase C sync not audited | Herald-0 on release milestone |
| **P2** | Neural Commons / Open Core issue templates still lack Phase/verification | Herald-0 batch pass |
| **P3** | Legacy `ROADMAP.md` deprecation banner | Compass-0 |
| **P3** | `INTELLECTUAL-EQUALITY.md` missing (referenced in pilot recruit doc) | Atlas-0 / Lex-0 |

## Skill gaps (for Nexus coaching profile)

| Capability | Gap | Suggested grow |
|------------|-----|----------------|
| `onboarding_docs` | 30-min bar verified manually only — no automated doc link CI beyond `health_check.py` | Pipeline-0 doc-link job |
| `protocol_sync` | Protocol v0.4 docs not auto-validated against OpenAPI on Atlas schema changes | Atlas-0 + Gauge-0 contract test handoff |
| `issue_templates` | 40+ templates; only 7 now have Phase/verification | Batch template pass next cycle |

## Nexus coaching patch applied

Merged **Nexus Training** and **Verification (`pocp-herald`)** sections; prior **Proven strengths** from `agents/patches/herald-0-2d1d8d4f.md` already in prompt.
