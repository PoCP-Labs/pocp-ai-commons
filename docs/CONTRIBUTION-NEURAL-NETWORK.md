# Contribution Neural Network

**PoCP as a verifiable, distributed intelligence network — not a single black-box model.**

See also: [NEURAL-INTERNET-MASTER-PLAN.md](./NEURAL-INTERNET-MASTER-PLAN.md) · [NEURAL-INTERNET-SUPPLY-SPEC.md](./NEURAL-INTERNET-SUPPLY-SPEC.md) · [CONTRIBUTION-INTERNET.md](./CONTRIBUTION-INTERNET.md) · [NEURAL-NETWORK-GITHUB-ADOPTION.md](./NEURAL-NETWORK-GITHUB-ADOPTION.md) · [PROTOCOL.md](./PROTOCOL.md) · [ARCHITECTURE-EVOLUTION.md](./ARCHITECTURE-EVOLUTION.md) · [Genesis (zh-CN) — §贡献神经网络](./genesis/zh-CN.md)

---

## One sentence

> **PoCP is a contribution neural network: Entities are neurons, verified contributions are signals, the ledger is memory, and intelligence is distributed across humans, agents, skills, and LLMs — auditable and open to all.**

中文：**PoCP 是一个贡献神经网络 — 算力与智力属于网络，不属于任何单一运营者。**

**Mission:** Build a **distributed intelligence + compute** network that breaks the capture of AI by a few hyperscale platforms and compute oligopolies — not by replacing one black box with another, but by making every link verifiable and every node able to run its own witness stack.

---

## Why this matters now

The AI era risks repeating the mobile-internet playbook at a larger scale:

| Oligopoly pattern | What gets captured |
|-------------------|-------------------|
| Compute gatekeeping | Who may run inference at all |
| API gatekeeping | Who may access “intelligence” |
| Account gatekeeping | Reputation and history |
| Economic gatekeeping | Subscription and token flows upward |

PoCP’s counter-design is **horizontal**, not **vertical**:

```text
Platform stack:     pay → one operator’s GPUs → opaque model → operator-owned memory
PoCP network:       contribute → many witnesses → portable proof → rights follow work → federated recognition
```

No single node is the brain. No single vendor is the only GPU. **The network is the unit of intelligence** — with cryptography, witness quorum, and traceable policy finalization where models stay opaque.

See [OPENNESS-AND-ANTI-MONOPOLY.md](./OPENNESS-AND-ANTI-MONOPOLY.md).

---

## Why this metaphor

In the AI era, value is created through **collaboration chains**:

```text
Human judgment + Agent execution + Skill specialization + LLM reasoning
→ verified contribution
→ rights and reputation
→ more collaboration
```

PoCP does not treat “AI platform” as one API endpoint. It treats the **whole network** as the unit of intelligence:

- Many entities participate in one contribution event.
- Many nodes may mirror and verify the same proof.
- Many LLMs may witness; **policy + quorum** finalizes traceably (any Entity type may delegate).

That is closer to a **neural network** than to a **chatbot SaaS** — with one critical difference: every link should be **verifiable**, not hidden inside weights.

---

## Architecture mapping

| Concept | PoCP primitive | Implementation (current / planned) |
|---------|----------------|----------------------------------|
| Neuron | Entity | `entities` table; Human, Agent, Skill, LLM, Organization |
| Synapse | Graph edge | `uses`, `calls`, `invokes_llm`, `verifies`, `submits` |
| Activation | Contribution Event | `contribution_events` + participants |
| Evidence | Local field | `evidence` + `content_hash` |
| Memory | Global state | Hash-chained `ledger_records` + graph Merkle + reputation |
| Forward pass | Invocation trace | Human → Agent → Skill → LLM |
| Validation | Verification layer | Multi-witness advisory + entity-equal policy finalization |
| Plasticity | Reputation / CP | Weighted by role; not purchasable |
| Federation | Multi-network | Signed proofs, trusted nodes, sync |

---

## Signal flow (one contribution)

```text
         ┌──────────┐
         │  Human   │──uses──► Agent ──calls──► Skill ──invokes_llm──► LLM
         └────┬─────┘                              │
              │ submits                            │
              ▼                                    │
         ┌─────────────┐◄── verifies ── Lumen-0 / DeSui
         │ Contribution │◄── sponsors ── Organization
         │    (hub)     │◄── finalizes ── Policy delegate (any Entity)
         └──────┬──────┘
                │
                ▼
         CP + AI Credits + Reputation
                │
                ▼
         Ledger memory (hash chain)
                │
                ▼
         More contribution (loop closes)
```

This is the **Genesis loop** expressed as network dynamics:

```text
Contribution → Verification → CP → AI Credits → AI Use → More Contribution
```

---

## Distributed compute and intelligence

“Super compute” in PoCP does **not** mean one operator runs the biggest GPU cluster.

It means:

1. **Horizontal entities** — specialized Agents and Skills compose on demand.
2. **Horizontal nodes** — communities run federated instances; mirrors serve read-only memory.
3. **Horizontal models** — multiple LLM witnesses (Lumen-0, DeSui, Clarion-0, local Ollama, provider APIs).
4. **Open protocol** — anyone can fork, deploy, verify anchors, import proofs.

### Breaking platform capture (engineering, not slogans)

| Layer | Anti-oligopoly mechanism | Code / config |
|-------|--------------------------|---------------|
| **Compute** | Node operators choose local or remote inference | `OllamaVerifier`, `OLLAMA_*`, future vLLM |
| **Intelligence** | Multi-witness advisory consensus, not one model score | `MultiVerifierService`, `neural_network_sources.yaml` |
| **Memory** | Hash-chained ledger + exportable proofs | `ledger_chain.py`, proof packets |
| **Topology** | Explicit peer trust, no global gatekeeper | `federation_*.py`, `POCP_TRUSTED_NODES` |
| **Rights** | Contribution → CP / AI Credits, not token-first | Genesis loop, [NO-TOKEN-FIRST.md](../NO-TOKEN-FIRST.md) |

The strongest structural move against monopoly is **plural operators**: schools, labs, regions, and communities each running a node that can verify — not merely consume — the same protocol.

See [OPENNESS-AND-ANTI-MONOPOLY.md](./OPENNESS-AND-ANTI-MONOPOLY.md) and [FEDERATION-v0.1.md](./FEDERATION-v0.1.md).

---

## What this is NOT

| Misread | PoCP stance |
|---------|-------------|
| One omniscient AI runs the network | AI is **advisory**; humans finalize |
| Opaque internal weights | **Portable proofs** and public ledger verify |
| Centralized brain company | **Multi-node federation** + MIT open source |
| Intelligence = token price | **Contribution-first**; see [NO-TOKEN-FIRST.md](../NO-TOKEN-FIRST.md) |
| Social credit surveillance | Reputation serves **collaboration**, not control |

---

## Engineering roadmap (this direction)

Building the neural network is **engineering**, not only narrative:

| Track | Epic / doc | Delivers |
|-------|------------|----------|
| Stable neuron activation | [Epic A #31](https://github.com/PoCP-Labs/pocp-ai-commons/issues/31) | Living loop on every node |
| Network scale (users) | [Epic B #29](https://github.com/PoCP-Labs/pocp-ai-commons/issues/29) | Real contributors, real edges |
| Visible graph | [Epic C #26](https://github.com/PoCP-Labs/pocp-ai-commons/issues/26) | Entity pages, graph explorer |
| Multi-brain federation | [Epic D #27](https://github.com/PoCP-Labs/pocp-ai-commons/issues/27) | Independent operators, sync |
| Network governance | [Epic E #25](https://github.com/PoCP-Labs/pocp-ai-commons/issues/25) | Contribution-weighted rules |
| Resource routing | [Epic F #30](https://github.com/PoCP-Labs/pocp-ai-commons/issues/30) | Sponsor pools |

Full tracker: [TOKEN-PATHWAY-EPICS.md](./TOKEN-PATHWAY-EPICS.md).

Current code touchpoints:

- `backend/services/graph.py` — graph construction
- `backend/services/invocation.py` — Human → Agent → Skill → LLM chain
- `backend/services/ledger_chain.py` — memory integrity
- `backend/services/federation_*.py` — multi-node nervous system
- `frontend/src/ContributionGraph.jsx` — visualization

---

## Guiding design rule

When adding a feature, ask:

```text
Does this strengthen a verifiable connection between entities,
or does it add opaque complexity?
```

If it strengthens **who contributed what, who verified it, and what rights follow** — it belongs in the network.

If it only adds UI without protocol memory — defer until the graph and ledger can record it.

---

## Related

- **[protocol/LANDING-PLAN-v0.1.md](./protocol/LANDING-PLAN-v0.1.md)** — actionable v0.4 neural base (start here for engineering)
- [protocol/NEURAL-ARCHITECTURE-v0.1.md](./protocol/NEURAL-ARCHITECTURE-v0.1.md) · [protocol/EXCHANGE-SPINE-v0.1.md](./protocol/EXCHANGE-SPINE-v0.1.md) · [protocol/CONSTITUTION-v0.1.md](./protocol/CONSTITUTION-v0.1.md)
- [GENESIS.md](../GENESIS.md) · [docs/genesis/zh-CN.md](./genesis/zh-CN.md)
- [INTELLIGENCE-LAYER.md](./INTELLIGENCE-LAYER.md)
- [VISION.md](./VISION.md)
