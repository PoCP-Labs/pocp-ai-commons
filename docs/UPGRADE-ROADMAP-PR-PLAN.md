# Upgrade Roadmap — Public GitHub vs Local vs PR Plan

**Audience:** Contributors, Agent Studio, PoCP-Labs maintainers.

**Conclusion up front:** The [public `main` branch](https://github.com/PoCP-Labs/pocp-ai-commons) still reads as **Genesis Loop / AI Commons app**. The **local workspace** (`graph-network-animation`, 15+ commits ahead) already implements large slices of the **Capability Internet Protocol** — but most of that is **not pushed to public GitHub yet**.

Parent vision: [CAPABILITY-INTERNET-PROTOCOL.md](./CAPABILITY-INTERNET-PROTOCOL.md)

**Patch applied:** `pocp_capability_internet_protocol_patch` (from Downloads) — see repo root `CAPABILITY-INTERNET-PROTOCOL.md`, `PROTOCOL-ROADMAP-PR-SEQUENCE.md`, and `backend/services/capability_internet/`.

---

## Three-layer product model

```text
Layer 1 — PoCP Capability Internet Protocol     (normative specs)
Layer 2 — PoCP Node / Entity Network            (reference implementation)
Layer 3 — PoCP AI Commons                       (first application — Genesis Loop)
```

Genesis Loop **stays**. Protocol upgrade **wraps** it — does not replace it.

---

## Public vs local — snapshot (2026-06)

| Concern | Public `main` (per review) | Local workspace |
|---------|---------------------------|-----------------|
| README positioning | “Earn AI access through contribution” only | Dual: Neural Commons + AI Commons first app |
| Python formatting | **Reported: files collapsed to 1 line on raw** | **Normal** — `main.py` ~288 lines, `contribution.py` ~354 |
| Entity types | 9 types | **14 types** incl. `compute_node`, `verifier_node`, `reviewer_node`, `sponsor`, `protocol_treasury` |
| Capability registry | Skill/Agent implicit | **`entity_capabilities` + registry API** |
| Invocation | Trace around initiator/skill/agent | Traces + steps; **PR-A `invocation_ref` on exchanges** |
| Settlement | Fixed reward in `approve_contribution` | Exchange spine + **settlement_policy** (PR-B WIP); contribution path still reward-function |
| Proof | Contribution evidence | Portable proof packets + export |
| NodeProfile table | None | **Metadata + compute_profile only** — no `node_profiles` table |
| Public node manifest | None | Spec only (`ENTITY-NODE-MANIFEST-v0.1.md`) |
| Protocol events | None | Ledger chain; no `protocol_events` table |
| CI / pyproject | Partial | `pyproject.toml`, `backend-ci.yml`, federation acceptance |
| Docs raw 404 | Reported on some paths | Local files exist under `docs/` |

**Action:** Pushing local branch to public `main` resolves PR-01 (formatting) and PR-02 (docs) for most items **if** the one-line issue was from an bad intermediate commit on public only.

Verify before push:

```powershell
git ls-files docs/PROTOCOL*.md docs/ARCHITECTURE.md
(Get-Content backend/main.py | Measure-Object -Line).Lines   # expect >> 1
python backend/scripts/smoke_test.py
```

---

## PR sequence (PR-01 … PR-15)

Status key: **Done (local)** · **Partial** · **Todo** · **Public only**

| PR | Title | Public | Local | Next action |
|----|--------|--------|-------|-------------|
| **PR-01** | Format backend Python source | Broken? | OK | Push + CI black/ruff gate |
| **PR-02** | README links & repo consistency | Gaps | Mostly OK | Audit links in CI; fix raw paths on push |
| **PR-03** | Reposition as Capability Internet | No | **Done** | Merge docs to public: `CAPABILITY-INTERNET-PROTOCOL.md`, `POCP-NETWORK-ARCHITECTURE.md` |
| **PR-04** | Extend EntityType for node network | 9 types | **14 types** | Add `relay_node`, `indexer_node`, `governance_node` (optional Phase B) |
| **PR-05** | NodeProfile + PublicNodeEndpoint | Todo | **Done (local)** | `node_profiles` + `POST /api/v1/nodes/*`, entity node-manifest |
| **PR-06** | Capability first-class | Todo | **Partial** | Already `EntityCapability`; align schema with protocol v0.3 + public node export |
| **PR-07** | Invocation capability ledger | Todo | **Done (local)** | `capability_invocations` table + `/api/v1/invocations/capability` + exchange spine link |
| **PR-08** | Proof + Verification protocol | Todo | **Partial** | `proofs` table; generalize beyond contribution; PR-B disputes |
| **PR-09** | Settlement layer (not reward fn) | Todo | **Partial** | Route `approve_contribution` → `SettlementRecord` → wallet |
| **PR-10** | TokenAccount CP/AIC/CC/PT | Todo | Partial | Extend wallet + `CreditType` |
| **PR-11** | Reputation graph upgrade | Todo | Partial | Scoped reputation + `graph_edges` event types |
| **PR-12** | ProtocolEvent append-only log | Todo | Todo | `protocol_events` + signed payload hash |
| **PR-13** | Public Skill Node closed loop | Todo | Todo | End-to-end demo per [MINIMUM-LIVING-NETWORK.md](./MINIMUM-LIVING-NETWORK.md) |
| **PR-14** | Security: signature / nonce / idempotency | Todo | Partial | Federation crypto exists; generalize to invocations |
| **PR-15** | SDK skeleton | Todo | Todo | `pocp-sdk-python` stub or `backend/sdk/` |

---

## Eight gaps — reconciled

| # | Gap (your analysis) | Local status | PR |
|---|---------------------|--------------|-----|
| 1 | README = AI Credits app only | Dual positioning in README + new protocol docs | PR-03 push |
| 2 | No NodeProfile | compute_profile JSON only | PR-05 |
| 3 | No Capability object | `EntityCapability` + registry | PR-06 finish |
| 4 | Invocation not bound to Capability | Legacy trace fields | PR-07 |
| 5 | No Proof object | export service, not `proofs` table | PR-08 |
| 6 | Verification not generic | contribution-scoped + PR-B | PR-08 |
| 7 | Reward not Settlement | exchange spine yes; approve path no | PR-09 |
| 8 | Graph not core asset | graph UI + entity connections | PR-11 |

---

## Issue groups (GitHub)

### Group 1 — Immediate (sync + health)

- [Repo Health] Verify Python formatting on public after push (PR-01)
- [Docs] Link check CI for README / docs (PR-02)
- [Architecture] Publish Capability Internet docs (PR-03)

### Group 2 — Protocol kernel (local → public)

- PR-04 … PR-10 (Entity → Settlement stack)
- Agent Studio plans: `phase_a_kernel`, `capability_internet`

### Group 3 — Network scale

- PR-11 … PR-15, P2P, IPFS, governance PIP, SDK

---

## Minimum living network (replaces “contribution only” demo)

Target loop: [MINIMUM-LIVING-NETWORK.md](./MINIMUM-LIVING-NETWORK.md)

**Exit:** Public Skill Node + signed invocation + proof + verification + settlement + graph — on **two federation nodes** where applicable.

---

## What not to do

- Do not delete Genesis Loop APIs — wrap them in Settlement
- Do not launch public token (PT internal only)
- Do not block on libp2p before HTTPS public nodes work
- Do not treat public GitHub snapshot as source of truth until local branch is merged

---

## Agent Studio

| Track | Doc |
|-------|-----|
| Phase A kernel | [agent-studio/PHASE-A-KERNEL-BACKLOG.md](./agent-studio/PHASE-A-KERNEL-BACKLOG.md) |
| Capability Internet (12 layers) | [agent-studio/CAPABILITY-INTERNET-BACKLOG.md](./agent-studio/CAPABILITY-INTERNET-BACKLOG.md) |
| PR upgrade sequence | [agent-studio/PR-UPGRADE-BACKLOG.md](./agent-studio/PR-UPGRADE-BACKLOG.md) |

Spawn:

```powershell
python backend/scripts/spawn_kernel_mission.py
python backend/scripts/spawn_capability_internet_mission.py
```

---

## One sentence

**Public repo = Genesis Loop shipped. Local repo = protocol kernel in progress. Next = push health + docs, then PR-05…PR-09 to turn reward functions into settlement protocol.**
