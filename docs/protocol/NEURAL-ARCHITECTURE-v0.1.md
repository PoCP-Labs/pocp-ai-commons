# Neural Architecture v0.1

**Formal model:** PoCP as a **verifiable neural network** for compute and intelligence exchange.

See [CONTRIBUTION-NEURAL-NETWORK.md](../CONTRIBUTION-NEURAL-NETWORK.md) for narrative; this document is **normative structure**.

---

## 1. Design thesis

| Biological | PoCP | Deliberate difference |
|------------|------|------------------------|
| Neuron | **Entity** (+ node facet) | Identity + crypto + manifest |
| Action potential | **Signal** (exchange / contribution) | Discrete events, not analog |
| Synapse | **Graph edge** | Typed, weighted, Merkle-committed |
| Long-term memory | **Memory chain** | Hash-linked, auditable |
| Plasticity | **Reputation / CP** | Does not rewrite ledger history |
| Brain in one skull | **Federation** | Many instances, opt-in trust |

PoCP **does not** simulate brains or train weights. It provides **infrastructure for verifiable collaboration** — the "nervous system" of the Contribution / AI Internet.

---

## 2. Three chains (链式神经)

One activation in the network touches **three chains**:

```text
┌─────────────────────────────────────────────────────────────┐
│  SIGNAL CHAIN — 算力/智力传导 (Execution)                      │
│  exchange_intent → invoke → receipt → exchange_settled       │
│  Artifacts: InvocationTrace, CapabilityReceipt, usage meters   │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│  STRUCTURE CHAIN — 突触拓扑 (Topology)                         │
│  Graph edges: uses, invokes, verifies, settles, provides       │
│  Artifacts: Contribution Graph, graph_merkle_root              │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│  MEMORY CHAIN — 不可篡改状态 (State)                           │
│  GRC: rights (CP/BC) · ELC: per-entity participation view      │
│  Artifacts: ledger_records, credit_transactions, anchor        │
└─────────────────────────────────────────────────────────────┘
```

### 2.1 Signal chain

**Purpose:** Record **how** compute and intelligence moved between Entities.

- **Input:** Consumer Entity requests capability (skill, gpu_inference, witness).
- **Propagation:** Agent orchestrates steps; each hop is an invocation step.
- **Output:** Receipt hash + usage; triggers settlement.

**Current code:** `invocation.py`, `capability_execute.py`, `compute_settlement.py`, `ai_chat.py`.

**Gap:** Events use different ledger `event_type` strings; must unify under `exchange_settled` envelope.

### 2.2 Structure chain

**Purpose:** Record **who connected to whom** for collaboration and routing.

- Edges carry `role`, `weight`, timestamps.
- Merkle root in anchor enables SPV: "this contribution's edges committed at time T".

**Current code:** `graph.py`, `graph_merkle.py`.

**Gap:** Exchange-only interactions (chat burn without contribution) should still add graph edges where policy requires.

### 2.3 Memory chain

**Purpose:** Record **rights changes and finalization** nobody can silently rewrite.

- **GRC (Global Rights Chain):** instance-wide serial append of rights-changing facts.
- **ELC (Entity Local Chain):** each Entity's ordered list of participations with SPV proofs into GRC/CGC.

**Current code:** `ledger_chain.py`, `wallet_audit.py`, `wallet_ledger_link.py` (heuristic).

**Gap:** `credit_transactions.ledger_record_id` FK; ELC API; atomic finalize batch.

---

## 3. One neural activation (end-to-end)

```text
Phase A — Signal
  Consumer Entity → quote → exchange_intent
  Provider Entities execute → invocation_trace + receipt

Phase B — Validation
  Witness Entities attest (advisory scores)
  Policy engine: PASS | ESCALATE | FAIL

Phase C — Structure
  Graph edges materialized for all participants

Phase D — Memory
  exchange_settled → credit_transactions → ledger_record
  (optional) contribution finalize → CP mint
  anchor bump (roots + cosign)

Phase E — Local view
  Each participant Entity updates ELC head (or mirror fetches SPV)
```

---

## 4. Entity types as neural specialties

| Entity type | Primary neural role | Signal | Structure | Memory |
|-------------|---------------------|--------|-----------|--------|
| Human | Sensory/motor — intent, consume | initiates | submits | wallet + ELC |
| Agent | Interneuron — orchestration | relay | uses/calls | ELC |
| Skill | Specialized cortex — capability | provides | skill_provider | ELC |
| LLM | Thalamus — inference/witness | provides/witness | invokes_llm/verifies | ELC |
| Compute Node | Muscle — FLOPS | gpu provider | provides | ELC |
| Organization | Hippocampus — archive | pool/sponsor | owns | archive GRC |
| Community | Brainstem — trust/routing | federation | trust edges | trust registry |

Any Entity may hold **multiple roles** via node manifest.

---

## 5. Plasticity vs immutability

| Mechanism | Plastic (可塑) | Immutable (不可改) |
|-----------|----------------|-------------------|
| Reputation scores | ✅ update | — |
| Graph edge weights (advisory) | ✅ | — |
| CP/BC balances | — | ✅ via new tx rows only |
| Ledger history | — | ✅ append-only |
| Witness scores on past events | — | ✅ frozen at attest time |

---

## 6. Relation to v0.3 schemas

| v0.3 schema | Neural chain |
|-------------|--------------|
| [CAPABILITY-SCHEMA-v0.3.md](./CAPABILITY-SCHEMA-v0.3.md) | Signal (what is exchanged) |
| [INVOCATION-SCHEMA-v0.3.md](./INVOCATION-SCHEMA-v0.3.md) | Signal propagation path |
| [SETTLEMENT-SCHEMA-v0.3.md](./SETTLEMENT-SCHEMA-v0.3.md) | Memory (rights) |
| [ENTITY-SCHEMA-v0.3.md](./ENTITY-SCHEMA-v0.3.md) | Neuron identity |
| [COMPUTE-NODE-SCHEMA-v0.3.md](./COMPUTE-NODE-SCHEMA-v0.3.md) | Compute muscle neuron |

v0.4 adds **EXCHANGE-SPINE** as the glue event model across all three chains.
