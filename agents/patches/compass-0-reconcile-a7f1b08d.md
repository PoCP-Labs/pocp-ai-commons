# Handoff reconciliation — active queue vs ROADMAP priorities

**Handoff:** `a7f1b08d-c2d8-469d-9b53-9b16995f3d3b`  
**Mission:** none (global queue)  
**Agent:** `pocp-agent-compass-0`  
**Generated:** 2026-06-02

## Handoff — Compass-0

- **Scope:** `[Nexus Research]` Reconcile active handoffs vs ROADMAP priorities; propose priority adjustments to Nexus.
- **Files:**
  - `agents/patches/compass-0-reconcile-a7f1b08d.md` — this report
  - `docs/ROADMAP-THREE-PHASES.md` — tracking row (latest reconcile pointer)
- **Tests run:** `python agents/scripts/roadmap_handoff_crosscheck.py`; `pytest -q tests/test_meta_agent_registry.py tests/test_pilot_metrics.py`; `python backend/scripts/ensure_meta_agents.py`
- **Result:** pass (cross-check PASS; analysis complete — Nexus should still thin meta queue)
- **Blockers:** none for Compass writable paths
- **Skill gaps:** none
- **Next agent:** **Nexus-0** (apply priority adjustments below); **Gauge-0** / **Vault-0** / **Mesh-0** (P0 engineering); **Herald-0** (mark `e2131c5b` completed)

---

## ROADMAP anchor (local optimization NOW)

| ROADMAP tier | Item | Owner |
|--------------|------|-------|
| **P0** | Exchange Spine E2E | Vault + Mesh + Gauge |
| **P0** | Wallet transaction replay | Vault + Gauge |
| **P1** | Federation L1 exchange import | Mesh |
| **P1** | Live compute adapter wire | Grid |
| **P1** | Pilot metrics CI artifact | Gauge + Pipeline |
| **P2** | CIP skeleton (does not preempt P0) | Atlas + Forge + Gauge |
| **P2** | Protocol Layer EDP | Atlas + Vault + Mesh |
| **P2** | Frontend federation demo UX | Canvas |

Source: [docs/ROADMAP-THREE-PHASES.md](../../docs/ROADMAP-THREE-PHASES.md) § Local optimization track; Herald sync: [nexus-research-gaps-e2131c5b.md](./nexus-research-gaps-e2131c5b.md).

---

## Queue snapshot (2026-06-02)

| Metric | Value |
|--------|------:|
| handoffs_total | 223 |
| open (pending + in_progress) | **169** |
| open P0 engineering (Vault/Mesh/Gauge) | **11** |
| blocked P0 engineering | **0** |
| cross-check script | **PASS** |

**Open queue by class:**

| Class | Count | ROADMAP alignment |
|-------|------:|-----------------|
| Nexus Training | 52 | Low — coaching; patches already landed for Compass/Herald |
| Nexus Review | 55 | Low — status noise; defer until P0 verify green |
| Nexus Research | 26 | Medium — doc sync; Herald `e2131c5b` **done** (patch landed) |
| Engineering | 15 | **High** — P0 exchange/wallet/federation + PA kernel + CI wave |
| Other | 21 | Mixed — PL issues, PM status, CIP publish |

**Delta vs prior reconcile (`a86cc259`, 2026-06-01):** P0 engineering moved from **48 blocked / 0 open** to **0 blocked / 11 open**. Meta queue grew (~11 → ~133 open meta items). Cross-check flipped FAIL → PASS because P0 is re-queued; **meta bloat is now the primary misalignment**, not P0 starvation.

---

## Misalignment findings

1. **Meta queue dominates Cursor dispatch** — 133/169 open handoffs are Training/Research/Review. Only 11 are P0 engineering. Without `pick_pending_handoffs` bias, meta cycles will run ahead of Vault `fad4296b`, Mesh `2d2ae075`, Gauge `f445c183` / `09554510`.
2. **Duplicate reconcile/research handoffs** — Compass Research appears ≥12× (`a7f1b08d`, `1527d19f`, `92f541a6`, …); Herald Research ≥8×. **Complete** `a7f1b08d` via this patch; bulk-close duplicates after cooldown.
3. **Herald Research satisfied** — `e2131c5b` patch reports pass (CIP docs indexed, ROADMAP P2 row). Handoff still **pending** in DB → mark **completed**; do not respawn until cooldown.
4. **CI wave vs ROADMAP P2 rule** — Open CI-1…CI-12 + Nexus CI gate (`bc91cffd`) are **engineering** but ROADMAP places CIP at **P2** (parallel to EDP, not before Exchange Spine). Sequence: **P0 → PA-4 → CI wave**, not CI ahead of `fad4296b`.
5. **PA kernel competes with P0** — `PROJECT_GOALS` lists PA-1…PA-4 at priority 0 alongside `p0_exchange_spine`. ROADMAP: finish Exchange/Wallet acceptance before expanding kernel surface. Gate PA-3/PA-6 behind PA-4 federation green.
6. **Doc gaps (P2/P3, non-blocking)** — per Herald: CIP not in CI, PR 4 runtime APIs, legacy ROADMAP banner, `INTELLECTUAL-EQUALITY.md`. Compass owns P3 banner when P0 stable.

---

## Priority adjustments proposed to Nexus-0

### Immediate (dispatch order)

| # | Action | Rationale |
|---|--------|-----------|
| 1 | **Cursor priority:** Vault `fad4296b` → Mesh `2d2ae075` → Gauge `f445c183` / `09554510` → PA-4 `a02e9037` / `d8c3d9df` before any meta handoff | ROADMAP P0 exit; matches `PROJECT_GOALS` P0 |
| 2 | **Pause** new Nexus Training + Nexus Review spawns until open meta &lt; 20 or P0 handoffs **completed** | 133 meta items add no Phase A exit signal |
| 3 | **Mark completed:** Herald `e2131c5b`; Compass `a7f1b08d` (this); bulk-close duplicate Research/Training IDs (keep newest per agent) | Reduces `pending_handoff_count`; prior patches exist |
| 4 | **Defer CI-*** engineering handoffs until `run_phase_a_acceptance.py --federation` green on P0 stack | ROADMAP P2; Herald gap P1 = CIP in CI only after local P0 |
| 5 | **Defer PL-*** protocol-layer issues until PA-4 green or explicit `protocol_layer_edp` mission active | P2 track; `abf89ad0` PL-9 acceptance is post-kernel |

### After P0 + PA-4 green

| # | Action | Rationale |
|---|--------|-----------|
| 6 | Run PA-1 entity catalog → PA-2 invocation → PA-3 settlement in order | `phase_a_kernel` plan sequence |
| 7 | Gauge `6d4cf132` consolidate + gate merge | Valid only after verify handoffs PASS |
| 8 | Resume Herald Research on cooldown for P2 doc gaps (Genesis, OpenAPI validation) | Herald `e2131c5b` gaps table |
| 9 | CI wave + `bc91cffd` minimum living network CI gate | `capability_internet_wave1` priority 1 in autopilot |

### Explicitly lower than P0 (do not promote)

- Nexus PM status `22811b1d`, `32ccfb7d`, `c565f5d2` — informational  
- Pilot metrics CI — P1 per ROADMAP; after local P0  
- Compass P3: legacy `ROADMAP.md` deprecation banner — Compass when meta queue thinned  

---

## Ranked backlog for Nexus dispatch (next 7 days)

| Rank | Phase | Task | Assignee | Exit / acceptance |
|------|-------|------|----------|-------------------|
| 1 | P0 | Exchange Spine + wallet audit | Vault-0 | `fad4296b`; pytest exchange/wallet; acceptance |
| 2 | P0 | Federation exchange proof E2E | Mesh-0 | `2d2ae075`; `run_phase_a_acceptance.py --federation` |
| 3 | P0 | Verify wallet + exchange + federation | Gauge-0 | `f445c183`, `09554510`; full pytest + acceptance |
| 4 | P0 | PA-4 federation acceptance restart | Mesh-0 + Gauge-0 | `a02e9037`, `d8c3d9df` |
| 5 | PA | PA-1 → PA-2 → PA-3 kernel chain | Atlas, Vault, Forge | `PROJECT_GOALS` exit signals |
| 6 | P1 | CIP demo in CI | Gauge-0 + Pipeline-0 | `minimum_living_network.py` in workflow |
| 7 | P2 | CIP runtime APIs (PR 4) | Forge-0, Pulse-0 | STAGED-PR-PLAN |
| 8 | P2 | Legacy ROADMAP.md banner | Compass-0 | single-file deprecation |

---

## Cross-check command

```bash
python agents/scripts/roadmap_handoff_crosscheck.py
# PASS when P0 engineering open and not blocked-only; re-run after meta dedupe
```

## Issue acceptance criteria (for Nexus issue emit)

| Issue theme | Phase | Acceptance command |
|-------------|-------|-------------------|
| Exchange / wallet | P0 | `python backend/scripts/run_phase_a_acceptance.py http://127.0.0.1:8100 --federation http://127.0.0.1:8101` |
| CIP skeleton | P2 | `python backend/scripts/minimum_living_network.py` |
| Pilot gate | P1 | `python backend/scripts/pilot_metrics.py <url> --json` |
| Meta agent roster | — | `pytest -q tests/test_meta_agent_registry.py tests/test_pilot_metrics.py` |
