# Nexus Research — doc sync report (Herald-0)

**Handoff:** `be66c695-7e65-4463-a876-7eb45a98ef12`  
**Mission:** `fa62e623-a98e-464e-b6e7-3f4ab95e992d`  
**Agent:** `pocp-agent-herald-0`  
**Generated:** 2026-06-01

## Handoff — Herald-0

- **Scope:** `[Nexus Research]` Sync roadmap/protocol review findings into `docs/` and onboarding; report gaps to Nexus-0.
- **Files:**
  - `docs/LOCAL-SETUP.md` — Entity Dialogue API examples (manifest + ping curl), protocol layer test command, EDP cross-links
  - `docs/README.md` — ENTITY-DIALOGUE-PROTOCOL + protocol-layer-edp MANIFEST in protocol index
  - `docs/ROADMAP-THREE-PHASES.md` — P2 Protocol Layer EDP row (parallel to local optimization P0)
  - `README.md` — Development Status P2 EDP row
  - `CONTRIBUTOR-QUALITY-GUIDE.md` — protocol layer pytest + spec links
  - `agents/patches/nexus-research-gaps-be66c695.md` — this report
- **Tests run:** `pytest tests/test_meta_agent_registry.py`; `ensure_meta_agents.py`; `health_check.py`; `pytest tests/test_entity_dialogue.py`; issue-template Phase coverage grep; README link spot-check
- **Result:** pass
- **Blockers:** none for Herald writable paths
- **Next agent:** Atlas-0 (PL-1 EDP spec audit, BINDING-TO-DIALOGUE.md); Gauge-0 (PL-9 protocol acceptance gate); Compass-0 (legacy ROADMAP.md deprecation banner)

## Sync completed this cycle

| Area | Action |
|------|--------|
| Protocol layer PL-8 | LOCAL-SETUP dialogue onboarding — manifest curl, authenticated ping example, `test_entity_dialogue` command |
| Roadmap alignment | ROADMAP-THREE-PHASES + README Development Status — P2 EDP track (does not preempt Exchange Spine P0) |
| Docs index | `docs/README.md` — ENTITY-DIALOGUE-PROTOCOL + protocol-layer-edp MANIFEST |
| Contributor guide | CONTRIBUTOR-QUALITY-GUIDE — protocol layer verification commands |

## Prior cycles (already landed)

See `agents/patches/nexus-research-gaps-f1e009ff.md`, `nexus-research-gaps-9a9e9811.md`, `herald-0-training-93d4ab5c.md` — ENTITY-EQUALITY, Meta Agents README section, issue template Phase & verification, CURSOR-AUTOMATION in LOCAL-SETUP, local optimization P0 table.

## Gaps remaining (for Nexus / domain agents)

| Priority | Gap | Suggested owner |
|----------|-----|-----------------|
| **P1** | `docs/protocol/BINDING-TO-DIALOGUE.md` missing (PL-5) | Atlas-0 + Pulse-0 |
| **P2** | Genesis translations (zh-CN / de) Phase C sync not audited | Herald-0 on release milestone |
| **P2** | Protocol v0.4 docs not auto-validated against OpenAPI on schema changes | Atlas-0 + Gauge-0 |
| **P3** | Legacy [ROADMAP.md](../../ROADMAP.md) deprecation banner | Compass-0 |
| **P3** | `INTELLECTUAL-EQUALITY.md` referenced in pilot recruit doc but missing | Atlas-0 / Lex-0 |
| **P3** | Automated doc link CI beyond `health_check.py` | Pipeline-0 |

## Nexus research corpus alignment

No new `RESEARCH_CORPUS` paths — protocol layer mission manifest now indexed from `docs/README.md`.
