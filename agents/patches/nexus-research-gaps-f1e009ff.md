# Nexus Research — doc gaps report (Herald-0)

**Handoff:** `f1e009ff-1c19-4f22-9f9d-de60c1dba6b1`  
**Mission:** `fa62e623-a98e-464e-b6e7-3f4ab95e992d`  
**Agent:** `pocp-agent-herald-0`  
**Generated:** 2026-06-01

## Sync completed this cycle

| Area | Action |
|------|--------|
| Missing doc | Created [docs/ENTITY-EQUALITY.md](../docs/ENTITY-EQUALITY.md) — referenced from README, pilot docs, HUMAN-REVIEW-GUIDE |
| README roadmap | Replaced legacy Phase 0–4 table with Phase A/B/C aligned to [ROADMAP-THREE-PHASES.md](../docs/ROADMAP-THREE-PHASES.md) |
| README onboarding | Added Meta Agents & Agent Studio section |
| docs/README.md | Added Meta Agents, Agent Studio, protocol v0.4 index, architecture/10, ENTITY-EQUALITY |
| docs/ARCHITECTURE.md | Added Agent Studio & Meta Agents layer |
| docs/LOCAL-SETUP.md | Fixed broken `./docs/*` links; added Meta Agent / Agent Studio onboarding |
| CONTRIBUTOR-QUALITY-GUIDE.md | Added Phase A acceptance commands + roadmap pointer |
| herald-0 prompt | Merged Nexus coaching strengths + `[Nexus Research]` handoff duty |

## Gaps remaining (for Nexus / domain agents)

| Priority | Gap | Suggested owner |
|----------|-----|-----------------|
| **P1** | Issue templates lack standard verification commands (`run_phase_a_acceptance.py`, federation flags) | Herald-0 (needs `.github/ISSUE_TEMPLATE/**` scope) or Forge-0 |
| **P1** | `docs/ROADMAP-THREE-PHASES.md` local optimization P0 items (Exchange Spine, Wallet replay) not reflected in README Development Status | Compass-0 + Herald-0 |
| **P2** | Genesis translations (zh-CN / de) Phase C sync not audited this cycle | Herald-0 on release milestone |
| **P2** | `docs/protocol/README.md` v0.4 index not cross-linked from root README protocol section | Herald-0 |
| **P2** | Agent Studio v1.2 Cursor automation (`agents/CURSOR-AUTOMATION.md`) not in LOCAL-SETUP onboarding path | Herald-0 + Pipeline-0 |
| **P3** | Legacy [ROADMAP.md](../ROADMAP.md) still exists alongside three-phase doc — may confuse new contributors | Compass-0 to add deprecation banner |
| **P3** | `INTELLECTUAL-EQUALITY.md` referenced in PILOT-FINALIZER-RECRUIT but missing | Atlas-0 / Lex-0 |

## Nexus research corpus alignment

Corpus paths from `nexus_learning.RESEARCH_CORPUS` are now indexed in `docs/README.md`:

- `docs/ROADMAP-THREE-PHASES.md` ✓
- `docs/ARCHITECTURE.md` ✓ (Agent Studio added)
- `docs/protocol/` ✓ (index linked)
- `agents/ROSTER.md` ✓ (already linked from agents/README)
- `NEURAL-COMMONS-ROADMAP.md` ✓ (existing index)
- `docs/PILOT-LAUNCH-CHECKLIST.md` ✓
- `backend/scripts/run_phase_a_acceptance.py` ✓ (CONTRIBUTOR-QUALITY-GUIDE + LOCAL-SETUP)

## Blockers

None for Herald-0 writable paths. Issue template updates blocked by handoff scope (no `.github/**` write).

## Next agent

- **Compass-0** — reconcile open handoffs vs ROADMAP P0/P1 priorities (paired research handoff)
- **Atlas-0** — review ENTITY-EQUALITY.md against protocol/CONSTITUTION-v0.1
