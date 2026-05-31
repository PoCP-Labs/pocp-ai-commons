# Three-Phase Roadmap — Protocol · Intelligence · Compute

**Status:** Phase A engineering milestone **done** (`v0.3.0-alpha`); **Phase A complete** pending public staging.  
**Release:** [`v0.3.0-alpha`](https://github.com/PoCP-Labs/pocp-ai-commons/releases/tag/v0.3.0-alpha) on `graph-network-animation`.  
**Local federation acceptance:** `run_phase_a_acceptance.py` green on node-a :8100 + node-b :8101.  
**North star:** Forkable **protocol + distributed intelligence + distributed compute** — not transaction-layer SaaS.

**Neural Commons** (v0.3 docs + v0.4 kernel) supports this path — it is not a separate product track. See [alignment](#neural-commons-alignment) below.

See also: [DISTRIBUTED-LAYERS.md](./DISTRIBUTED-LAYERS.md) · [ACCOUNTABILITY-BOUNDARY.md](./ACCOUNTABILITY-BOUNDARY.md) · [genesis/zh-CN.md](./genesis/zh-CN.md) §6 · [../NEURAL-COMMONS-ROADMAP.md](../NEURAL-COMMONS-ROADMAP.md)

---

## Phase A milestone definition (canonical)

| Milestone | What it means | Status |
|-----------|---------------|--------|
| **`v0.3.0-alpha`** | Phase A **documentation + engineering** land: acceptance runner, federation E2E green, Neural Commons v0.3 docs, v0.4 Entity/Capability kernel, Open Core quality tooling, proof verify UI | **Done** |
| **Phase A complete** | **Public staging** live: Postgres, GitHub OAuth, `ENABLE_DEV_LOGIN=false`, `run_phase_a_acceptance.py` green against staging API | **Remaining** |

Do not call Phase A finished until staging passes acceptance. Do not delay tagging or docs for staging — `v0.3.0-alpha` is the engineering checkpoint; staging is the public exit gate.

---

## Execution priority (NOW → NEXT)

```text
v0.3.0-alpha ✅  →  public staging (Phase A complete)  →  Phase B
Phase B         →  operable multi-node compute/MCP  →  30-day third-party peer
Phase C         →  protocol SDK  →  2+ forks exchange proof packets
```

**Rule:** Do not skip Phase A exit criteria for architecture-only work. Neural Commons v0.4+ code lands **inside** Phase A/B themes (Entity registry → Phase B compute profile; Capability registry → Phase C market).

**Release sequencing (canonical):** Land **public staging** and pass staging acceptance **before** committing the Wallet / Federation settlement wave (Wave 2). Staging proves the OAuth + Postgres path; Wave 2 builds on that foundation in separate PRs.

---

## Neural Commons alignment

| Phase | Neural Commons work | Maps to |
|-------|---------------------|---------|
| **A** | v0.3 docs, acceptance runner, proof export/verify UI | Demonstrable public loop |
| **A→B** | v0.4 Entity + Capability kernel, compute node types | ComputeProfile + scheduler |
| **B** | v0.5–v0.7 invocation, settlement, rule-based routing | Multi-node receipts in proof |
| **C** | Protocol SDK, unified capability market on Entity graph | Cross-app federation |

---

## Overview

| Phase | Horizon | Goal | Success signal |
|-------|---------|------|----------------|
| **A** | 4–8 weeks | **Demonstrable public loop** — fork → run → verify contribution in 30 min | `run_phase_a_acceptance.py` green; staging with OAuth |
| **B** | 2–4 months | **Operable distributed network** — multi-node compute/MCP normal | Third-party peer node 30 days uptime |
| **C** | 6–12 months | **Contribution Internet prototype** — protocol forked by other apps | 2+ apps exchange same proof/federation format |

---

## Phase A — Demonstrable public loop (NOW)

### P0 — Must ship

**Engineering milestone (`v0.3.0-alpha`) — done**

- [x] **Acceptance runner** — `backend/scripts/run_phase_a_acceptance.py`
- [x] **One-command local** — `scripts/run-phase-a.ps1` / `scripts/run-phase-a.sh`
- [x] **CI: unit + smoke** — `.github/workflows/smoke-test.yml`
- [x] **CI: federation acceptance** — `.github/workflows/phase-a-federation.yml`
- [x] **Git tag** `v0.3.0-alpha` — pushed to GitHub
- [x] Local federation acceptance green

**Phase A complete — staging exit gate**

- [ ] **Public staging** — Postgres + GitHub OAuth; `ENABLE_DEV_LOGIN=false`
- [ ] **Staging acceptance** — `run_phase_a_acceptance.py https://api.<staging-host> --staging --skip-optional` (or `scripts/run-staging-acceptance.ps1`)
- [ ] **Staging env verify** — `scripts/verify-staging.ps1` passes on production `backend/.env`

### P1 — Should ship in Phase A

- [x] Federation demo: peer witness E2E (`peer_witness_verify_test.py`)
- [x] Federation MCP E2E (`peer_mcp_demo_test.py`)
- [x] CrewAI witness registration + E2E script (`crewai_witness_e2e_test.py`)
- [x] Local federation acceptance green (`run_phase_a_acceptance.py --federation`)
- [ ] Staging: `ENABLE_CREWAI_WITNESS=true` on demo/staging instance
- [ ] Pilot metrics gate in CI (optional `--strict` threshold for pilot launch, not demo stack)

### P2 — Nice in Phase A

- [x] Frontend: proof URL deep-link (`?proof=<contribution_id>` → Verify Proof tab)
- [x] `docs/LOCAL-SETUP.md` aligned with Phase A scripts

### Run Phase A locally

**Single node (Postgres + API + frontend):**

```bash
# Windows
.\scripts\run-phase-a.ps1

# Linux / macOS
./scripts/run-phase-a.sh
```

**Federation (node-a :8100, node-b :8101):**

```bash
.\scripts\run-phase-a.ps1 -Federation
# or
./scripts/run-phase-a.sh --federation
```

**Acceptance only (stack already up):**

```bash
python backend/scripts/run_phase_a_acceptance.py http://127.0.0.1:8000
python backend/scripts/run_phase_a_acceptance.py http://127.0.0.1:8100 --federation http://127.0.0.1:8101
```

**Public staging (OAuth, no dev-login):**

```bash
# On the server after deploy — verify backend/.env first
./scripts/verify-staging.sh
python backend/scripts/run_phase_a_acceptance.py https://api.your-domain.com --staging --skip-optional

# Or one command from repo root (local machine with backend/.env configured)
./scripts/run-staging-acceptance.sh https://api.your-domain.com
```

---

## Phase B — Operable distributed network

### Themes

1. **ComputeProfile + scheduler** — Entities declare witness / embed / MCP; receipts in proof
2. **Cross-node embedding** — `POST /intelligence/compute/embed` on peers
3. **MCP production** — stable live client; peer live MCP with `POCP_PEER_MCP_REMOTE_MODE=live`
4. **GNN advisory v0.2** — optional PyG layer; explainable review queue
5. **Governance automation** — parameterized finalization; org maintainer bots

### Exit criteria

- Third-party operator runs a trusted peer from published docs ≥ 30 days
- Compute scheduler routes ≥ 1 real witness job off-node with receipt in proof

---

## Phase C — Contribution Internet prototype

### Themes

1. **Protocol SDK** — lightweight client: submit, verify, export proof, federation import
2. **Unified capability market** — AgentSkills + MCP + OpenClaw catalog discovery on Entity graph
3. **Rights portability** — optional cross-instance CP/Credits policy (instance sovereignty)
4. **Multi-app federation** — 2+ independent forks exchange contributions

### Exit criteria

- Two external projects import PoCP proof packets without forking AI Commons UI
- Genesis translations (en / zh-CN / de) synced per release milestone

---

## Tracking

| Artifact | Location |
|----------|----------|
| Phase A acceptance | `backend/scripts/run_phase_a_acceptance.py` |
| Federation CI | `.github/workflows/phase-a-federation.yml` |
| Staging env template | `backend/.env.staging.example` |
| Staging env verify | `backend/scripts/verify_staging_env.py` · `scripts/verify-staging.ps1` |
| Staging acceptance | `scripts/run-staging-acceptance.ps1` · `--staging` on acceptance runner |
| Public deploy guide | [PUBLIC-DEPLOY.md](./PUBLIC-DEPLOY.md) |
| Federation compose | `docker-compose.federation.yml` |
| Pilot checklist | [PILOT-LAUNCH-CHECKLIST.md](./PILOT-LAUNCH-CHECKLIST.md) |

**Principle unchanged:** automation-first, traceable finalization — intelligence can live in AI; rights memory cannot live in a black box.
