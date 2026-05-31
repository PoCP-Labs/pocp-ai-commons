# Distributed Intelligence Layer — Open-Source Benchmark

**Mapping mature GitHub / OSS patterns to PoCP’s intelligence orchestration plane.**

See also: [DISTRIBUTED-INTELLIGENCE.md](./DISTRIBUTED-INTELLIGENCE.md) · [DISTRIBUTED-LAYERS.md](./DISTRIBUTED-LAYERS.md) · [NEURAL-NETWORK-GITHUB-ADOPTION.md](./NEURAL-NETWORK-GITHUB-ADOPTION.md) · [external_inspirations.yaml](../backend/config/external_inspirations.yaml) · [neural_network_sources.yaml](../backend/config/neural_network_sources.yaml)

**English canonical.** Chinese context: [genesis/zh-CN.md](./genesis/zh-CN.md).

---

## Purpose

PoCP’s **Distributed Intelligence Layer** is not a single upstream project. It combines:

```text
Orchestration  +  Witness quorum  +  Matching  +  Graph advisory  +  Compute routing
        ↓
Contribution → Proof → Human finalization → Ledger
```

This benchmark answers:

1. Which OSS projects cover which slice?
2. What does PoCP already ship?
3. What should we **borrow** (adapter), **reject**, or **defer**?
4. Where does each item land in code / config?

> **Guiding rule:** AI witnesses. Policy finalizes. Ledger remembers.

---

## Contribution Settlement Layer (PoCP position)

No single upstream project equals **PoCP Neural Commons Network**. The market splits by layer:

| Layer | Representative projects | What they optimize | PoCP role |
|-------|-------------------------|-------------------|-----------|
| AI intelligence market | Bittensor, SingularityNET | Subnet / service marketplace + token incentive | **Declined** token loop; borrow capability taxonomy only |
| AI training network | Gensyn | Decentralized train / verify / trade | Training as **contribution type** + ComputeReceipt |
| Compute marketplace | Akash, Render, io.net, Aethir | GPU supply and job market | **Compute Adapter** — external Entity source |
| Agent economy | Fetch.ai, Virtuals, Agent Economy research | Agent payment and assetization | Agent as **Entity** + InvocationTrace; **decline** agent coins |
| Tool protocol | MCP | Agent ↔ tool wiring | **Integrated** — PoCP records post-invoke proof |
| Public goods / graph | Gitcoin, SourceCred, CHAOSS | Funding and dependency graphs | **Advisory** graph hints — never auto-finalize |
| Intelligent Internet | II (ii.inc) | Account + agent + compute signals | **Research** benchmark for multi-signal profiles |

### What PoCP adds (the missing layer)

```text
Who joined the task?
Which capability was invoked (LLM / Skill / Tool / Compute)?
Was output verified?
Who finalized?
How were CP / AI Credits / reputation updated?
What is the portable Proof + graph edge?
```

Registry: `external_inspirations.yaml` (round 8) · Compute: [COMPUTE-ADAPTER-SPEC.md](./COMPUTE-ADAPTER-SPEC.md)

**One-line:** Others build **resource markets**; PoCP builds **contribution proof + multi-entity settlement + reputation graph** after resources are invoked.

---

## Capability matrix

| PoCP intelligence capability | Primary code today | OSS benchmark | PoCP coverage | Adapter priority |
|------------------------------|-------------------|---------------|---------------|------------------|
| Multi-Entity collaboration chain | `capability_execute.py`, `invocation.py` | LangGraph, AutoGen, CrewAI | **Partial** — StudyAgent + CrewAI witness | P1 — extend InvocationTrace |
| Agent ↔ agent discovery & tasks | `intelligence/router`, peer compute | **A2A** ([a2aproject/A2A](https://github.com/a2aproject/A2A)) | **Gap** — no Agent Card yet | **P0** |
| Agent ↔ tool / data | MCP invoke path | **MCP** ([modelcontextprotocol/spec](https://github.com/modelcontextprotocol/spec)) | **Active** — inspiration mapped | P1 — harden receipts on MCP steps |
| Multi-witness advisory consensus | `verifiers/multi_verifier.py` | Meritocrab, OCTP, CrewAI | **Active** | P2 — external verifier plugins |
| Witness diversity / quorum | `finalization.py`, `multi_verifier.py` | AGT trust tiers (analogy) | **Active** — env pilot | P1 — yaml default |
| Capability matching | `intelligence/engines.run_matching` | sentence-transformers, HF | **Active** — embeddings blend | P2 |
| Graph analytics (advisory) | `graph_analytics.py`, PyG | SourceCred, PyG, DGL | **Partial** — PageRank hints | P2 — advisory only |
| Compute job routing | `compute_scheduler.py`, `compute_executor.py` | Ollama, vLLM, llama.cpp | **Active** | P1 — peer mesh hardening |
| Compute attribution receipts | `compute_receipt.py`, `compute_attribution.py` | TrustlessInference, ProvenanceKit | **Active** — off-chain receipts | P2 — optional TEE fields |
| Peer overlay (NN-5) | `peer_compute.py`, federation | ForgeFed, Matrix | **Partial** — secret + import | P1 |
| Agent identity & sponsor | Entity model, federation sig | **AGT / AgentMesh** ([microsoft/agent-governance-toolkit](https://github.com/microsoft/agent-governance-toolkit)) | **Partial** — Entity owner | **P0** — handshake patterns |
| Contribution provenance | `provenance.py`, Proof packet | OCTP, ProvenanceKit, Morkeeth receipt | **Active** | P1 — EAA extension alignment |
| Human finalization | `finalization.py`, review UI | *(rare in agent mesh stacks)* | **Unique to PoCP** | — |
| Portable proof + ledger | `proof.py`, `ledger_chain.py` | Bitcoin-style chain, ForgeFed export | **Active** | — |
| Token-miner compute markets | — | Bittensor, 0G, zkai | **Declined** — NO-TOKEN-FIRST | ❌ |

---

## Layer map (what to borrow from where)

```text
┌─────────────────────────────────────────────────────────────────┐
│  PoCP Protocol (unique spine)                                   │
│  Entity · Contribution · Proof · InvocationTrace · Ledger       │
└───────────────────────────────▲─────────────────────────────────┘
                                │
┌───────────────────────────────┴─────────────────────────────────┐
│  Distributed Intelligence (this benchmark)                        │
│                                                                 │
│  Orchestration ← A2A, LangGraph, AutoGen, CrewAI                  │
│  Trust mesh    ← AGT (sponsor, audit log, handshake)            │
│  Witness       ← Meritocrab, OCTP, multi-LLM verifiers          │
│  Matching      ← sentence-transformers, Ollama embed            │
│  Graph hints   ← SourceCred (advisory), PyG                     │
│  Routing       ← ComputeProfile scheduler + peer_compute        │
│  Attribution   ← ProvenanceKit EAA, ComputeReceipt             │
│  Federation    ← ForgeFed import patterns                       │
└───────────────────────────────▲─────────────────────────────────┘
                                │
┌───────────────────────────────┴─────────────────────────────────┐
│  Distributed Compute (adapters only)                            │
│  Ollama · vLLM · llama.cpp · OpenAI · DeepSeek · peer inference │
└─────────────────────────────────────────────────────────────────┘
```

---

## Project profiles

### P0 — Adopt interface patterns next

#### Google A2A (Agent2Agent)

| Field | Value |
|-------|-------|
| Repo | [a2aproject/A2A](https://github.com/a2aproject/A2A) |
| License | Apache-2.0 |
| Borrow | Agent Card (`/.well-known/agent.json`), JSON-RPC task lifecycle, cross-framework delegation |
| Reject | Replacing PoCP Contribution / Proof with A2A task state as source of truth |
| PoCP target | `GET /.well-known/pocp-agent.json` per Entity; map A2A `Task` → `ContributionEvent` + `InvocationTrace` |
| Registry | `neural_network_sources.yaml` → `a2a_protocol` |
| Status | **adapter_planned** |

**Complement:** MCP handles agent→tool; A2A handles agent→agent. PoCP Entity is both.

#### Microsoft Agent Governance Toolkit (AgentMesh)

| Field | Value |
|-------|-------|
| Repo | [microsoft/agent-governance-toolkit](https://github.com/microsoft/agent-governance-toolkit) |
| License | Apache-2.0 (check subpackages) |
| Borrow | Human sponsor binding, Ed25519 identity, short-lived credentials, Merkle audit log, peer handshake |
| Reject | Trust score auto-gating without human review; enterprise-only compliance as hard requirement |
| PoCP target | Align `federation` signatures + `peer_compute` secret with IATP-style handshake; optional `AuditLog` export on Proof |
| Registry | `neural_network_sources.yaml` → `agent_governance_toolkit` |
| Status | **evaluating** |

---

### P1 — Strengthen existing modules

#### ProvenanceKit (EAA model)

| Field | Value |
|-------|-------|
| Repo | [Arttribute/provenancekit](https://github.com/Arttribute/provenancekit) |
| Borrow | Entity / Action / Attribution graph; `ext:witness`, `ext:ai`, `ext:contrib` extensions |
| Reject | On-chain settlement as default loop |
| PoCP target | Proof packet extension blocks; map ComputeReceipt → `ext:witness` shape |
| Inspiration registry | Candidate for `external_inspirations.yaml` |
| Status | **evaluating** |

#### ForgeFed

| Field | Value |
|-------|-------|
| Repo | [ForgeFed/ForgeFed](https://github.com/ForgeFed/ForgeFed) |
| Borrow | Federated activity, portable object IDs, cross-forge trust |
| PoCP target | Already in `external_inspirations.yaml`; extend `federation_import.py` discovery |
| Status | **pattern_borrowed** |

#### OriginTrail DKG

| Field | Value |
|-------|-------|
| Repo | [OriginTrail/dkg](https://github.com/OriginTrail/dkg) |
| Borrow | Knowledge Asset + Merkle anchor mental model for multi-agent memory |
| Reject | Mandatory blockchain node for every operator |
| PoCP target | Optional export of Proof subgraph as portable Knowledge Asset JSON |
| Status | **research** |

---

### P2 — Advisory / optional hardening

| Project | Borrow | PoCP module | Constraint |
|---------|--------|-------------|------------|
| [sourcecred/sourcecred](https://github.com/sourcecred/sourcecred) | Contribution graph reputation | `graph_analytics.py` | **Advisory only** — never auto-approve |
| [pyg-team/pytorch_geometric](https://github.com/pyg-team/pytorch_geometric) | GNN review priority hints | `graph_analytics.py` | Same |
| [lfglabs-dev/TrustlessInference](https://github.com/lfglabs-dev/TrustlessInference) | TEE attestation fields on inference | `compute_receipt.py` | Optional; federation-safe |
| [blackwell-systems/knowing](https://github.com/blackwell-systems/knowing) | Merkle code graph + MCP | Skill / code contribution path | Research |

---

### Already active in PoCP (no new benchmark work)

| Project | PoCP use | Config / code |
|---------|----------|---------------|
| OpenAI / DeepSeek APIs | Witness neurons | `verifiers/` |
| Ollama | Local witness + embed | `ollama_client.py`, `compute_nodes.yaml` |
| vLLM / llama.cpp | Community witness nodes | `vllm_client.py`, `llama_cpp_client.py` |
| sentence-transformers | Match + dedup | `sentence_embedder.py` |
| LangGraph | StudyAgent runtime | `study_agent_runtime.py` |
| CrewAI | Multi-agent witness crew | `crewai_witness.py` |
| MCP | Tool invoke | `remote_mcp_invoke.py`, inspiration `mcp` |
| OCTP / GARL / Meritocrab | Protocol patterns | `external_inspirations.yaml` |
| ERC-8004 | Agent trust pattern (off-chain) | inspiration entity |

---

### Declined (policy)

| Project | Reason | Registry slug |
|---------|--------|---------------|
| [agentcommons/agent-commons](https://github.com/agentcommons/agent-commons) | Token-first economics | `agent-commons` |
| Bittensor subnets | Token-miner marketplace; conflicts with bilateral credits model | `bittensor` |
| Virtuals Protocol | Agent-native token issuance | `virtuals-protocol` |
| Surveillance / social-credit scoring | Violates human-finalization principle | — |

### Evaluating (round 8 — benchmark registered)

| Project | Borrow | Reject | Registry slug |
|---------|--------|--------|---------------|
| Gensyn | Training attestation, verifier plugins | On-chain training market as spine | `gensyn` |
| Akash | Compute adapter, provider registration | AKT as PoCP currency | `akash` |
| Render Network | GPU adapter, job metering | RNDR settlement loop | `render-network` |
| Gitcoin / Deep Funding | Dependency graph hints (advisory) | Grant vote as finalization | `gitcoin` |
| Intelligent Internet | Account+agent bundle, compute signals | Mandatory chain PoP | `intelligent-internet` |
| SingularityNET | Service discovery → capability import | AGIX marketplace spine | `singularitynet` |
| Fetch.ai | Multi-agent delegation → InvocationTrace | FET payment loop | `fetch-ai` |
| ProvenanceKit | EAA proof extensions | On-chain default settlement | `provenancekit` |

See [inspiration-mappings/](./inspiration-mappings/) and [COMPUTE-ADAPTER-SPEC.md](./COMPUTE-ADAPTER-SPEC.md).

See [NO-TOKEN-FIRST.md](../NO-TOKEN-FIRST.md) and `declined_inspirations` in `external_inspirations.yaml`.

---

## Gap analysis (what no OSS stack gives you)

These are **PoCP differentiators** — do not expect to find a drop-in replacement:

1. **Human finalization gate** — most agent meshes stop at task `completed`.
2. **Contribution-bound compute** — anti-abuse requires `contribution_id` / `task_id` on jobs.
3. **Portable Proof Packet** — federation import with hybrid crypto suite.
4. **Entity-native service matrix** — nine Entity types with roles, not generic agents.
5. **Ledger memory** — CP / AI Credits settlement tied to approved contributions.
6. **Advisory-only intelligence** — graph / GNN / trust scores cannot auto-finalize.

---

## Recommended adapter roadmap

| Phase | Goal | Upstream | PoCP deliverable |
|-------|------|----------|------------------|
| **BI-1** | External discoverability | A2A | Agent Card endpoint ✅ |
| **BI-1.5** | Task → Contribution | A2A JSON-RPC | `SendMessage` / `GetTask` / `ListTasks` ✅ |
| **BI-2** | Peer trust hardening | AGT | Handshake headers + challenge endpoint ✅; Proof audit log (open) |
| **BI-3** | Receipt schema alignment | ProvenanceKit | Proof `ext:witness` / `ext:ai` blocks |
| **BI-4** | Federation memory export | OriginTrail DKG (optional) | Proof subgraph export JSON |
| **BI-5** | TEE-ready receipts | TrustlessInference | Optional `integrity.tee_attestation` on ComputeReceipt |

Track in [DEV-TASKS.md](../DEV-TASKS.md) under Distributed Intelligence Layer.

---

## Contributor workflow

```text
1. Pick a row from the capability matrix (gap or P0/P1).
2. Open issue: Neural Network Adoption or Code Contribution task.
3. Add / update entry in neural_network_sources.yaml OR external_inspirations.yaml.
4. Implement thin adapter — no fork of upstream repo.
5. Tests + section in EXTERNAL-INTEGRATIONS.md.
6. Human review → contribution → ledger record.
```

**Issue templates:** `.github/ISSUE_TEMPLATE/neural_network_adoption_task.md`

---

## Quick reference — best composite stack for PoCP

If assembling a **reference architecture** from OSS (without replacing PoCP protocol):

```text
A2A + MCP          → orchestration & tools
AGT                → peer identity & audit
Meritocrab / OCTP  → witness plugins & provenance
ProvenanceKit EAA  → attribution extensions
ForgeFed           → federation portability
Ollama / vLLM      → compute adapters
PoCP Protocol      → finalization, ledger, proof export  ← non-negotiable spine
```

---

## Related docs

| Doc | Role |
|-----|------|
| [INTELLIGENCE-LAYER.md](./INTELLIGENCE-LAYER.md) | Capability module catalog |
| [EXTERNAL-INTEGRATIONS.md](./EXTERNAL-INTEGRATIONS.md) | Implemented borrowings |
| [inspiration-mappings/](./inspiration-mappings/) | Per-project protocol mappings |
| [DISTRIBUTED-COMPUTE-RESEARCH.md](./DISTRIBUTED-COMPUTE-RESEARCH.md) | Compute layer deep dive |

---

## One-line summary

> **PoCP’s distributed intelligence layer is a composable orchestration plane built from A2A/MCP/AGT/Meritocrab-class OSS — anchored by a protocol spine no agent marketplace provides: verifiable contributions, human approval, and ledger memory.**
