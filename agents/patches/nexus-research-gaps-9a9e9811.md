# Nexus Research — doc sync report (Herald-0)

**Handoff:** `9a9e9811-56c9-430b-b714-72d8e024d1b8`  
**Mission:** `fa62e623-a98e-464e-b6e7-3f4ab95e992d`  
**Agent:** `pocp-agent-herald-0`  
**Generated:** 2026-06-01

## Handoff — Herald-0

- **Scope:** `[Nexus Research]` Sync roadmap/protocol review findings into `docs/` and onboarding; report gaps to Nexus-0.
- **Files:** see Sync completed below
- **Tests run:** `pytest tests/test_meta_agent_registry.py`; `ensure_meta_agents.py`; `health_check.py`; issue-template Phase coverage grep
- **Result:** pass
- **Blockers:** none for Herald writable paths
- **Next agent:** Compass-0 (legacy ROADMAP deprecation banner); Atlas-0 (ENTITY-EQUALITY vs CONSTITUTION-v0.1); Pipeline-0 (doc-link CI)

## Sync completed this cycle

| Area | Action |
|------|--------|
| Local optimization onboarding | [docs/LOCAL-SETUP.md](../docs/LOCAL-SETUP.md) — P0 federation acceptance + protocol v0.4 / EXCHANGE-SPINE links |
| Contributor guide | [CONTRIBUTOR-QUALITY-GUIDE.md](../CONTRIBUTOR-QUALITY-GUIDE.md) — local optimization P0 exit signals |
| README Meta Agents | [README.md](../README.md) — CURSOR-AUTOMATION cross-link |
| Docs index | [docs/README.md](../docs/README.md) — local optimization + protocol v0.4 in Development & operations |
| Issue templates | 21 domain templates now include **Phase & verification** (Neural Commons, Open Core, Sprint Alpha, review/skill/research) |
| Herald skill | [.cursor/skills/pocp-herald/SKILL.md](../.cursor/skills/pocp-herald/SKILL.md) — writable paths aligned with prompt (`.github/ISSUE_TEMPLATE/**`) |

## Prior cycles (already landed)

From `agents/patches/nexus-research-gaps-f1e009ff.md` and `herald-0-training-93d4ab5c.md`:

- ENTITY-EQUALITY.md, README Phase A/B/C roadmap, Meta Agents section, docs index, ARCHITECTURE Agent Studio layer
- Core issue templates (code, test, bug, feature, good-first, pilot, issue_spec)
- README Development Status local P0 table; Genesis Package protocol v0.4 link

## Gaps remaining (for Nexus / domain agents)

| Priority | Gap | Suggested owner |
|----------|-----|-----------------|
| **P2** | Genesis translations (zh-CN / de) Phase C sync not audited | Herald-0 on release milestone |
| **P2** | Protocol v0.4 docs not auto-validated against OpenAPI on Atlas schema changes | Atlas-0 + Gauge-0 |
| **P3** | Legacy [ROADMAP.md](../ROADMAP.md) deprecation banner | Compass-0 |
| **P3** | `INTELLECTUAL-EQUALITY.md` referenced in pilot recruit doc but missing | Atlas-0 / Lex-0 |
| **P3** | Automated doc link CI beyond `health_check.py` | Pipeline-0 |

## Nexus research corpus alignment

All `nexus_learning.RESEARCH_CORPUS` paths indexed in `docs/README.md` — no new corpus paths this cycle.
