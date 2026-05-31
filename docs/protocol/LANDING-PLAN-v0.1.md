# PoCP Neural Base — Landing Plan v0.1

**Purpose:** Turn the neural-network + exchange-spine theory into **shippable engineering** with phases, acceptance criteria, and PR-sized tasks.

**Audience:** Protocol designers, backend/frontend engineers, node operators.

**Related specs:** [CONSTITUTION-v0.1.md](./CONSTITUTION-v0.1.md) · [NEURAL-ARCHITECTURE-v0.1.md](./NEURAL-ARCHITECTURE-v0.1.md) · [EXCHANGE-SPINE-v0.1.md](./EXCHANGE-SPINE-v0.1.md) · [ENTITY-NODE-MANIFEST-v0.1.md](./ENTITY-NODE-MANIFEST-v0.1.md)

---

## Executive summary

PoCP is **contribution infrastructure for the AI era**: a verifiable network where **Entities are neurons**, **graph edges are synapses**, and **three chains** record signals (exchange), structure (topology), and memory (rights).

The **exchange spine** makes the ledger the pathway for **compute + intelligence** — not only contribution points. Bitcoin-style verify layers (hash chain, Merkle, SPV, wallet replay) apply **internally**; external narrative stays contribution-first.

**What exists today (v0.3 codebase):**

- Living loop: submit → witness → finalize → CP/BC
- Wallet: quote, summary, transactions, export verify
- Ledger verify, graph Merkle, federation import, proof packets
- Compute settlement with `compute_provided` / `compute_consumed` ledger events

**What v0.4 adds:**

- Unified **exchange_settled** events + FK binding to credit transactions
- **Entity node manifest** + **ELC** read API
- **Constitution** enforced in CI
- Proof packet **exchange_inclusion** layer

---

## Theory stack (one page)

```text
Layer 4 — Experience     Dashboard, Chat, Wallet, Graph explorer
Layer 3 — Policy         Finalization, quorum, issuance_budget, federation L0–L3
Layer 2 — Exchange       Capability invoke, compute settlement, AI chat (Signal chain)
Layer 1 — Memory         GRC ledger, credit_transactions, anchor (Memory chain)
Layer 0 — Topology       Contribution graph, Merkle (Structure chain)
Layer -1 — Verify        audit_node, proof verify, wallet replay, SPV
```

**Guiding rule:** Memory before marketplace; chain before app; verify before trust; policy before permission.

---

## Metaphor → spec → code → gap

| Metaphor | Normative spec | Current module | Gap | Priority |
|----------|----------------|----------------|-----|----------|
| Neuron | ENTITY-SCHEMA, NODE-MANIFEST | `models/entity.py` | No manifest API | P1 |
| Action potential | EXCHANGE-SPINE | `compute_settlement.py`, `ai_chat.py` | Fragmented event types | **P0** |
| Synapse | Graph edges | `graph.py` | Exchange-only edges optional | P2 |
| Long-term memory | GRC ledger | `ledger_chain.py` | — | ✅ |
| Plasticity | Reputation / CP | `contribution.py` | — | ✅ |
| Local memory | ELC | — | Not implemented | P1 |
| SPV | Proof + Merkle | `proof_export.py` | No `exchange_inclusion` | P1 |
| Wallet audit | Constitution Art. I.4 | `wallet_audit.py` | Heuristic ledger link | P0 |
| Witness neuron | Manifest witness role | `MultiVerifierService` | Missing `witness_entity_id` sign block | P1 |
| Federation synapse | FEDERATION-v0.1 | `federation_*.py` | L0–L3 not formalized in import | P2 |

---

## Phase roadmap

### Phase 0 — Constitution lock (1–2 weeks)

**Goal:** Define "protocol bugs" and test them.

| Task | Files | Acceptance |
|------|-------|------------|
| Add `test_constitution.py` | `backend/tests/` | CI fails on deliberate violations |
| Document checklist in PR template | `.github/` | PRs reference Constitution |
| Smoke asserts wallet replay | `scripts/smoke_test.py` | export verify passes |

**Exit criteria:** 5+ constitution tests green; smoke includes wallet + ledger verify.

---

### Phase 1 — Exchange spine wedge (2–3 weeks) **P0**

**Goal:** One function emits all BC-moving settlements; ledger ↔ tx is atomic.

| Task | Detail |
|------|--------|
| `exchange_spine.py` | `emit_exchange_settled()` wrapper |
| Migrate callers | `compute_settlement.py`, `ai_chat.py`, `federation_settlement.py` |
| DB migration | `credit_transactions.ledger_record_id` nullable → required for new rows |
| `finalize_exchange_settlement()` | Single transaction: txs + ledger |
| Wallet link | Prefer FK over heuristic in `wallet_ledger_link.py` |
| Tests | Settlement rollback if ledger fails; FK present |

**Ledger payload example:**

```json
{
  "event_type": "exchange_settled",
  "payload": {
    "exchange_kind": "hybrid",
    "receipt_hash": "sha256:…",
    "credit_transaction_ids": ["…"],
    "legacy_event_type": "compute_provided"
  }
}
```

**Exit criteria:**

- All new BC movements have `exchange_settled` + `ledger_record_id` on credit tx
- `GET /wallets/me/transactions` shows category from payload, not guess
- Constitution tests 6–8 pass

---

### Phase 2 — Entity node surface (2 weeks) **P1**

**Goal:** Entity = node is visible in API and UI.

| Task | Detail |
|------|--------|
| Schema | `NodeManifestV01` pydantic model |
| API | `GET /api/v1/entities/{id}/node-manifest` |
| Well-known | `GET /.well-known/pocp-node.json` (instance archive entity) |
| Witness block | Persist `witness_entity_id` + signature on attest |
| Frontend | Entity profile: roles badge (Witness, Capability, …) |

**Exit criteria:**

- Every seeded LLM Entity returns manifest with `roles: ["witness"]`
- Proof export includes witness block with entity_id

---

### Phase 3 — ELC + exchange_inclusion (2–3 weeks) **P1**

**Goal:** Lightweight clients verify participation without full ledger.

| Task | Detail |
|------|--------|
| `EntityLocalChainService` | Append on settlement + finalize hooks |
| API | `GET /entities/{id}/local-chain` |
| Proof | Add `exchange_inclusion` to proof packet schema |
| Verify | `POST /proof/verify` checks exchange layer |

**Exit criteria:**

- Human Entity after chat shows ELC head with `exchange_settled` ref
- Offline verify links receipt → ledger SPV

---

### Phase 4 — Anchor + federation hardening (3–4 weeks) **P2**

| Task | Detail |
|------|--------|
| Optional `exchange_merkle_root` in anchor | See EXCHANGE-SPINE §7 |
| Import levels L0–L3 | Flag on `federation_import.py` |
| Docker acceptance | Two-node federation in CI |
| `audit_node.py remote` in smoke | Post-deploy checklist |

**L0–L3 summary:**

| Level | Import rights | Default |
|-------|---------------|---------|
| L0 | Metadata only, no BC | — |
| L1 | Read + verify proofs | **default** |
| L2 | BC mirror with proof | opt-in |
| L3 | Full settlement peer | trusted partners |

---

### Phase 5 — Network scale (ongoing)

Tracks from [CONTRIBUTION-NEURAL-NETWORK.md](../CONTRIBUTION-NEURAL-NETWORK.md): Epic A–F (living loop, users, graph, federation, governance, sponsor pools).

Neural base **enables** scale; does not replace product epics.

---

## First PR bundle (recommended order)

```text
PR-1  exchange_spine.py + tests (no caller migration yet)
PR-2  compute_settlement + ai_chat → emit_exchange_settled
PR-3  migration ledger_record_id + wallet FK link
PR-4  test_constitution.py (Articles I–II)
PR-5  GET node-manifest + schema
PR-6  witness_entity_id in attest persistence
PR-7  ELC service + read API
PR-8  proof exchange_inclusion
```

Each PR ≤ 400 lines where possible; independently reviewable.

---

## API additions summary

| Method | Path | Phase |
|--------|------|-------|
| GET | `/api/v1/entities/{id}/node-manifest` | 2 |
| GET | `/.well-known/pocp-node.json` | 2 |
| GET | `/api/v1/entities/{id}/local-chain` | 3 |
| GET | `/api/v1/exchanges/{id}` | 1 (optional read) |
| POST | `/api/v1/exchanges/verify` | 3 |

Existing wallet and ledger verify APIs **unchanged**.

---

## Operator runbook (minimal)

**Daily:**

```bash
python backend/scripts/smoke_test.py
python backend/scripts/audit_node.py remote --url https://your-node
```

**After deploy:**

1. `GET /api/v1/ledger/verify` → `valid: true`
2. `GET /api/v1/crypto/readiness` → suite OK
3. Export wallet → `POST /wallets/me/export/verify` → pass
4. Spot-check manifest for witness Entities

**Before federation peer:**

- Agree trust level L1 vs L2
- Exchange anchor root fingerprints
- Run import dry-run on staging

---

## Success metrics (90 days)

| Metric | Target |
|--------|--------|
| BC movements with `exchange_settled` | 100% new traffic |
| Credit tx with `ledger_record_id` | 100% new rows |
| Entities with published manifest | All providers + witnesses |
| Constitution tests | ≥ 12, all green |
| Independent audit pass rate | 100% on release candidates |
| Federation pairs with L1 import | ≥ 2 public demos |

---

## What we explicitly defer

| Item | Reason |
|------|--------|
| P2P gossip between Entities | Phase 5+; HTTP federation sufficient for v0.4 |
| On-chain anchor | Portable proof + optional external cosign first |
| Global identity / KYC | Community-scoped trust |
| Replacing all legacy event_type strings | `legacy_event_type` in metadata during migration |

---

## Document index

| File | Content |
|------|---------|
| [README.md](./README.md) | Protocol folder index |
| [CONSTITUTION-v0.1.md](./CONSTITUTION-v0.1.md) | Invariants |
| [NEURAL-ARCHITECTURE-v0.1.md](./NEURAL-ARCHITECTURE-v0.1.md) | Three chains theory |
| [EXCHANGE-SPINE-v0.1.md](./EXCHANGE-SPINE-v0.1.md) | Event model |
| [ENTITY-NODE-MANIFEST-v0.1.md](./ENTITY-NODE-MANIFEST-v0.1.md) | Node roles + ELC |
| [THREAT-MODEL-v0.1.md](./THREAT-MODEL-v0.1.md) | Security |

**Next action:** Implement **Phase 1 PR-1** (`exchange_spine.py`) unless you prefer starting with constitution tests first.
