# PoCP AI Commons — Platform Retrospective (2026-05)

**Scope:** Reference application of the Capability Internet Protocol (CIP)  
**Branch snapshot:** `capability-internet-protocol` (includes `6ddb1b6` exchange spine land)  
**Tests:** 511 collected (`pytest --collect-only`)  
**Status:** Local optimization track largely complete; public staging deferred by choice

---

## 1. Executive summary

PoCP AI Commons completed a **product–engineering pivot** from a contribution-first Genesis demo to a **capability-first exchange infrastructure**:

> **Anyone can sell compute and publish AI capabilities; anyone can buy by the unit; every exchange is Entity-attributed, metered, and ledger-auditable.**

The default user path is now **算力 + 能力** (metered invoke → receipt → BC settlement → wallet). The **Contribution Chain** (witness, CP, public graph) is an **opt-in upgrade** from exchange receipts—not a prerequisite for marketplace use.

**What is proven locally:**

- Exchange spine (`exchange_settled`) wired through AI chat, compute settlement, and capability execute fallback
- Entity Local Chain (ELC), portable exchange proofs with Merkle SPV
- Federation L1 exchange import on a **two-node Docker demo** (Node A → Node B, no BC mint on mirror)
- Optional `publish-contribution` from settled exchanges with witness + graph edges
- Wallet replay audit, Provider manifest/directory UI, org compute pool panel

**Current bottleneck:** not architecture—it is **narrative consistency**, **public staging**, and **real Provider/network scale**.

Canonical narrative: [CAPABILITY-FIRST-POSITIONING.md](./CAPABILITY-FIRST-POSITIONING.md)  
Engineering plan: [protocol/CHAIN-AND-NODE-PLAN-v0.1.md](./protocol/CHAIN-AND-NODE-PLAN-v0.1.md)

---

## 2. Strategic positioning

### 2.1 What we are / are not

| We are | We are not |
|--------|------------|
| Distributed **compute + capability** exchange on the existing Internet | A new physical network or blockchain L1 |
| Entity-attributed supply (PC, Skill, Agent, LLM, MCP tool) | Another bundled ChatGPT subscription |
| Metered invoke → receipt → BC settlement | Token-first miner marketplace |
| Optional contribution upgrade (CP, public graph) | “Define intelligence philosophically” on every invoke |

### 2.2 Architecture (2+1 chains)

```text
DEFAULT PATH
  quote → invoke + receipt → exchange_settled → credit_transactions → ledger (hash-linked)

OPTIONAL PATH
  exchange receipt → publish-contribution → witness → policy finalize → CP + graph

FEDERATION
  exchange proof (SPV) → L1 import on peer (advisory; no silent BC mint)
```

| Chain | Role | Primary code |
|-------|------|--------------|
| **Exchange** | Metered compute/capability invokes | `exchange_spine.py`, `compute_settlement.py`, `ai_chat.py` |
| **Ledger** | Append-only BC/CP memory | `ledger_chain.py`, `wallet_service.py` |
| **Contribution** (opt-in) | CP, witness, graph | `contribution.py`, `finalization.py`, `exchange_contribution.py` |

Invariants: [protocol/CONSTITUTION-v0.1.md](./protocol/CONSTITUTION-v0.1.md) — enforced in part by `tests/test_constitution.py`.

---

## 3. Implementation phases (capability-first plan)

| Phase | Goal | Status |
|-------|------|--------|
| **0** Narrative & schema lock | 算力+能力 UX, `exchange_kind` | ✅ |
| **1** Exchange wedge | `emit_exchange_settled`, FK `ledger_record_id`, C1–C2 tests | ✅ |
| **2** Provider surface | node manifest, directory, well-known, Provider UI | ✅ (signed receipt optional via `POCP_SIGN_COMPUTE_RECEIPTS`) |
| **3** ELC + proof + federation L1 | ELC API, exchange proof, import, verify routing | ✅ |
| **4** Instance pilot | publish-from-receipt, witness, graph edges, Docker demo | ✅ (no public multi-operator pilot yet) |

**Three-phase roadmap** ([ROADMAP-THREE-PHASES.md](./ROADMAP-THREE-PHASES.md)):

| Milestone | Status |
|-----------|--------|
| `v0.3.0-alpha` (Phase A docs + engineering) | ✅ Done |
| Local optimization (Exchange / Wallet / federation exchange) | ✅ Largely done |
| Public staging (OAuth, `ENABLE_DEV_LOGIN=false`) | ⏸ Deferred |
| Phase B (operable multi-node compute/MCP) | 🔜 Not started |
| Phase C (protocol SDK, third-party forks) | 🔜 Not started |

---

## 4. Engineering inventory

### 4.1 Backend (FastAPI)

**22 router modules** including:

- **Exchange:** `exchanges`, `exchange_spine`, `compute_settlement`, `ai_chat`, `capability_execute`
- **Provider:** `capabilities`, `compute`, `node_manifest`, `capability_registry`
- **Wallet:** `wallet`, `wallet_service`, `wallet_ledger_link`
- **Federation:** `federation`, `federation_exchange_import`, `federation_settlement`, hybrid PQC (`crypto_suite`)
- **Contribution (legacy + upgrade):** `api` contributions, `verification`, `finalization`
- **Extensions:** Agent Studio, CIP skeleton (`services/cip/`), Bitcoin-inspired event overlay, meta agents

**Key services added in exchange wave:**

| Module | Purpose |
|--------|---------|
| `exchange_spine.py` | Unified `exchange_settled` events |
| `entity_local_chain.py` | ELC read view over settlements |
| `exchange_proof.py` | Portable proof + Merkle inclusion |
| `federation_exchange_import.py` | L1 import (verify, no BC mint) |
| `exchange_contribution.py` | Opt-in contribution upgrade from exchange |
| `node_manifest.py` | Provider facet manifest |

### 4.2 Frontend (React)

| Surface | Components |
|---------|------------|
| 算力/能力 | `CapabilityDirectory`, `ProviderPanel`, `ComputePoolPanel` |
| Wallet | `WalletPanel`, `EntityWalletActivity`, `WalletTxRow` |
| Network | `ContributionGraph`, `EntityDetail` (ELC, 发布为贡献) |
| Contribute / Verify | `SubmitFlow`, `ProofVerifyPanel` |

### 4.3 Protocol documentation

Entry: [protocol/README.md](./protocol/README.md)  
CIP 12-layer spec index present; in-memory skeleton at `backend/services/cip/` — **not yet production primary path**.

### 4.4 Operations & acceptance

| Asset | Purpose |
|-------|---------|
| `docker-compose.federation.yml` | Node A `:8100`, Node B `:8101` |
| `scripts/smoke_test.py` | Genesis MVP loop |
| `scripts/federation_demo_test.py` | Epic D contribution federation |
| `scripts/federation_exchange_demo_test.py` | Exchange proof L1 demo |
| `scripts/run_phase_a_acceptance.py` | Full local acceptance |

**Verified locally (2026-05):** federation exchange demo green after hybrid signature verify fix (`federation_signatures_valid`).

---

## 5. End-to-end flows (what actually runs)

### 5.1 Default marketplace

```text
dev-login → POST /ai/chat (mock)
  → exchange_id + exchange_settled + receipt_hash
  → GET /wallets/me/transactions
  → GET /entities/{id}/local-chain
  → GET /exchanges/{id}/proof → POST /proof/verify
```

Compute: `ComputeReceipt` → `settle_bilateral` → `exchange_settled`  
Capability: `execute_skill` / `execute_agent` (fallback burn via `exchange_spine`)

### 5.2 Federation

```text
Node A: metered invoke → exchange proof (hybrid sign + SPV)
Node B: POST /federation/import-exchange-proof (L1, idempotent)
Parallel: contribution proof sync + cross-node reputation (Epic D)
```

### 5.3 Contribution upgrade (optional)

```text
POST /exchanges/{id}/publish-contribution
  → witness participant + exchange_upgrade evidence
  → graph: exchange --promoted_to--> contribution hub
  → existing auto-verify / finalize → CP
```

---

## 6. Quality posture

| Signal | Status |
|--------|--------|
| Unit/integration tests | 511 collected; exchange/wallet/federation suites green |
| Constitution C1–C2 | `test_constitution.py` |
| Federation Docker | `federation_exchange_demo_test.py` + `federation_demo_test.py` |
| Wallet replay | `GET /wallets/audit`, `test_wallet_me` |
| Live adapters | Akash live wire tests exist; production traffic minimal |

**Risks:** heavy mock verifier dependency; staging OAuth path untested in CI; some invoke paths still need exchange_spine audit for 100% coverage.

---

## 7. Gaps and technical debt

| Item | Severity | Notes |
|------|----------|-------|
| README vs capability-first narrative | Medium | Top-level README still Neural/Genesis heavy |
| `exchange_settled` coverage audit | Medium | OpenClaw / some federation paths |
| `POCP_REQUIRE_RECEIPT_SIGNATURE` | Medium | Default off; enable for production providers |
| `credit_transactions` ordering | Low | Same-second txs; wallet test uses explicit timestamps; consider `seq` column |
| CIP skeleton vs REST dual track | Medium | Needs convergence roadmap |
| PQC production | Low | dev-stub common; liboqs optional |
| Public staging | High (ops) | OAuth, disable dev-login, `--staging` acceptance |

### 7.1 Success metrics (90-day plan) vs reality

| Metric (CHAIN-AND-NODE-PLAN §9) | Reality (May 2026) |
|-----------------------------------|---------------------|
| ≥20 active capabilities | Seed/demo level |
| ≥1k monthly invokes | No production telemetry |
| ≥10 providers earning BC | Local demo only |
| 100% new traffic → `exchange_settled` | Engineering target met; needs CI gate |
| ≥1 federation pair (exchange import) | **Docker pair ✅**; public pair ❌ |

---

## 8. Competitive assessment

**Differentiation today:**

1. Entity-attributed, replay-auditable ledger (not opaque platform billing)
2. Portable contribution **and** exchange proofs + federation L1
3. Dual-path product: daily invoke without witness; CP/graph when promoted
4. Open Core + extensive specs → forkable campus/lab Instance

**Not yet moats:**

1. Real Provider network (GPU hosts, Skill authors)
2. Live compute adapter production traffic
3. Protocol SDK / third-party integrations (Phase C)
4. Unified quote-first invoke UX across all surfaces

---

## 9. Recommended PR split (review alignment)

Branch `capability-internet-protocol` is **already multi-commit** ahead of `main`. For review, prefer **thematic PRs** (stacked if needed):

| PR | Base | Commits / scope | Reviewer focus |
|----|------|-----------------|----------------|
| **PR-Exchange** | `main` | `6ddb1b6` + `2b7a98d` — spine, ELC, proof, federation L1 import, constitution tests | Protocol / ledger |
| **PR-Wallet** | `main` or PR-Exchange | wallet router, `wallet_service`, ledger link, UI panels | Wallet / audit |
| **PR-Provider** | `main` | manifest, directory, ProviderPanel, ComputePoolPanel | Marketplace UX |
| **PR-CIP-Wave1** | `main` | `f66dbc2`…`9e07401` — CIP skeleton, Wave 1 gate, Agent Studio polish | CIP / Agent Studio |
| **PR-Federation-Network** | `main` | addrbook, nodes UI, trust policy (`aa412d4`, `1bdd63b`) | Federation ops |

**Do not** force-split a single commit without user approval of history rewrite. Use cherry-pick branches from named commits when parallel review is needed.

---

## 10. P0 action checklist (next 4–8 weeks)

| Priority | Action | Exit signal |
|----------|--------|-------------|
| **P0** | Push branch; open stacked PRs per §9 | Reviewable diffs on GitHub |
| **P0** | Public staging runbook | `run_phase_a_acceptance.py --staging` green |
| **P1** | README first screen → capability-first | Links to `CAPABILITY-FIRST-POSITIONING.md` |
| **P1** | CI gate: new invokes must emit `exchange_settled` + FK | Constitution test in CI |
| **P1** | One real Provider pilot (1 PC + 1 Skill, 10 invokes/week) | Non-seed `exchange_settled` rows |
| **P2** | Live adapter doc + one public Ollama/Akash job | Receipt in production ledger |
| **P2** | Quote-first invoke UX (frontend) | Cost shown before every burn |
| **P3** | CIP skeleton ↔ REST convergence plan | Single documented primary path |

---

## 11. Conclusion

PoCP AI Commons is no longer “only a contribution demo.” It is a **verifiable compute/capability exchange reference** with:

- Unified settlement spine
- Portable proofs and cross-node L1 import
- Wallet audit and Provider onboarding surfaces
- An optional path to public contribution graph

The platform is **ready for staged public pilot** and **reviewable PR landing**—not for another large architecture phase. The next wins come from **staging, narrative polish, and real Providers**—not more spec volume.

---

## Related documents

- [CAPABILITY-FIRST-POSITIONING.md](./CAPABILITY-FIRST-POSITIONING.md)
- [protocol/CHAIN-AND-NODE-PLAN-v0.1.md](./protocol/CHAIN-AND-NODE-PLAN-v0.1.md)
- [ROADMAP-THREE-PHASES.md](./ROADMAP-THREE-PHASES.md)
- [protocol/EXCHANGE-SPINE-v0.1.md](./protocol/EXCHANGE-SPINE-v0.1.md)
- [protocol/CONSTITUTION-v0.1.md](./protocol/CONSTITUTION-v0.1.md)
