# Distributed Layers — Protocol · Compute · Intelligence

**North star:** Build PoCP as a **contribution neural network** with three cooperating layers — not a single-vendor SaaS stack. Mission context: [INTELLECTUAL-EQUALITY.md](./INTELLECTUAL-EQUALITY.md).

See also: [PROTOCOL-STACK.md](./PROTOCOL-STACK.md) · [CONTRIBUTION-NEURAL-NETWORK.md](./CONTRIBUTION-NEURAL-NETWORK.md) · [NEURAL-NETWORK-GITHUB-ADOPTION.md](./NEURAL-NETWORK-GITHUB-ADOPTION.md) · [ACCOUNTABILITY-BOUNDARY.md](./ACCOUNTABILITY-BOUNDARY.md) · [Language Policy](./LANGUAGE-POLICY.md)

---

## Three layers (one network)

```text
┌─────────────────────────────────────────────────────────────┐
│  Protocol Layer — portable, federated trust memory          │
│  Entity · Contribution · Evidence · Proof · InvocationTrace │
│  Finalization · Ledger · Federation signatures                │
└───────────────────────────▲─────────────────────────────────┘
                            │ operates on protocol objects
┌───────────────────────────┴─────────────────────────────────┐
│  Distributed Intelligence — witness quorum, agents, graph   │
│  Multi-witness quorum · Agents · Matching · Graph analytics │
│  Clarion · StudyAgent · Governance advisory · Dedup hints     │
└───────────────────────────▲─────────────────────────────────┘
                            │ consumes compute
┌───────────────────────────┴─────────────────────────────────┐
│  Distributed Compute — node-local inference & embeddings    │
│  Ollama · vLLM · llama.cpp · OpenAI · DeepSeek · HTTP plugins │
│  sentence-transformers · Ollama embeddings · compute registry │
└─────────────────────────────────────────────────────────────┘
```

| Layer | What we build | API / code |
|-------|---------------|------------|
| **Protocol** | Verifiable, portable, federated primitives | `services/proof.py`, `federation_*`, `ledger_chain.py` |
| **Distributed intelligence** | Witness consensus, agents, matching, graph analytics | `backend/intelligence/`, `graph_analytics.py` |
| **Distributed compute** | Per-node inference and embedding adapters | `verifiers/*`, `compute_nodes.yaml`, `compute_registry.py` |

Deep research: [DISTRIBUTED-COMPUTE-RESEARCH.md](./DISTRIBUTED-COMPUTE-RESEARCH.md) — feasibility, gaps, phased plan.

**Primer (中文):** [DISTRIBUTED-COMPUTE-PRIMER.md](./DISTRIBUTED-COMPUTE-PRIMER.md) — 是什么 · 接入 · 调度 · 与智力层结合 · Proof 闭环。

**完整方案（中文 canonical）：** [NEURAL-INTERNET-MASTER-PLAN.md](./NEURAL-INTERNET-MASTER-PLAN.md) — 供需 · 协议 · 联通 · 交易 · 调节 · 路线图。

**Support argument (中文):** [DISTRIBUTED-COMPUTE-SUPPORT-ARGUMENT.md](./DISTRIBUTED-COMPUTE-SUPPORT-ARGUMENT.md) — 当前实现能否支撑分布式算力层。

Implementation guide: [DISTRIBUTED-INTELLIGENCE.md](./DISTRIBUTED-INTELLIGENCE.md) — ComputeProfile, scheduler, Entity service matrix.

OSS benchmark (what to borrow): [DISTRIBUTED-INTELLIGENCE-BENCHMARK.md](./DISTRIBUTED-INTELLIGENCE-BENCHMARK.md).

Transaction layer (wallets, approve UI) stays **thin** — see [PROTOCOL-STACK.md](./PROTOCOL-STACK.md).

---

## Absorbing human-led latest results

PoCP **adopts** mature open ecosystems via thin adapters — not by rebuilding ChatGPT or PyTorch from scratch.

| Human-led ecosystem | PoCP adapter | Status |
|---------------------|--------------|--------|
| LangChain / LangGraph | StudyAgent orchestration | Partial — `backend/intelligence/agents/` |
| OpenAI / DeepSeek APIs | Witness verifiers | Active — `services/verifiers/` |
| Ollama / local runtimes | Node compute adapters | Optional — `compute_nodes.yaml` |
| sentence-transformers | Embeddings / dedup hints | Planned |
| AgentSkills / SKILL.md | Skill import path | Partial — capabilities router |

Details: [NEURAL-NETWORK-GITHUB-ADOPTION.md](./NEURAL-NETWORK-GITHUB-ADOPTION.md) · registry `backend/config/neural_network_sources.yaml`.

---

## Operator language

Platform UI, APIs, and canonical operator docs are **English-first**. See [LANGUAGE-POLICY.md](./LANGUAGE-POLICY.md). Genesis translations (e.g. Chinese) live under `docs/genesis/` and do not override runtime defaults.
