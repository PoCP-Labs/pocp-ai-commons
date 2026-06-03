# PoCP Capability Internet Protocol

> **PoCP is the decentralized contribution, invocation, settlement, and reputation protocol for AI capability and compute networks.**

> **PoCP 是面向 AI 能力与算力网络的去中心化贡献证明、能力调用、价值结算与声誉协议。**

**Tagline:** PoCP — the capability internet protocol for the AI era. · **PoCP：AI 时代的能力互联网协议。**

This document is the **canonical positioning** for PoCP-Labs. Implementation lives in [pocp-ai-commons](https://github.com/PoCP-Labs/pocp-ai-commons) as the first reference application; protocol specs live under `docs/protocol/` and `docs/architecture/`.

See also: [CAPABILITY-FIRST-POSITIONING.md](./CAPABILITY-FIRST-POSITIONING.md) · [protocol/README.md](./protocol/README.md) · [POCP-NETWORK-ARCHITECTURE.md](./POCP-NETWORK-ARCHITECTURE.md) · [MINIMUM-LIVING-NETWORK.md](./MINIMUM-LIVING-NETWORK.md) · [VISION.md](./VISION.md)

---

## Default loop (capability-first — locked)

**首屏路径（锁定）** — metered exchange, not contribution-first UX:

```text
quote → invoke → receipt → wallet (BC / AI Credits; ledger-auditable)
```

Publish compute or AI capabilities → consumer quotes → invokes → receives receipt → wallet reflects settlement. Protocol index: [protocol/README.md](./protocol/README.md) · repo entry: [../README.md](../README.md#default-loop-capability-exchange).

**Contribution upgrade (optional):** witness review, CP, public graph, and governance participation — **not required** for marketplace invoke. See [Minimum living network](#minimum-living-network) and [CAPABILITY-FIRST-POSITIONING.md](./CAPABILITY-FIRST-POSITIONING.md).

---

## What PoCP is

PoCP is **not** a chat app, centralized task marketplace, points gimmick, GPU-only market, generic agent platform, or public token launch.

PoCP **is**:

| Layer | Role |
|-------|------|
| AI capability protocol | Who can do what, in a standard schema |
| Contribution proof protocol | What was contributed, with verifiable evidence |
| Invocation ledger | Who invoked whom, with hashes and receipts |
| Multi-party settlement | How value splits across participants |
| Distributed reputation graph | Contextual trust, not a single score |
| Usage metering | CP, AIC, CC, PT — measure before tokenize |
| Entity Node network | Any Entity may become a PoCP Node |

---

## Core questions

Every layer must help answer:

```text
Who provides what capability?
Who invoked whom?
Who contributed what?
Who proved what?
Who verified what?
Who should receive what?
Who becomes more trusted?
Who may participate in governance?
```

---

## Network subjects: Entity

**User** = login account. **Entity** = network subject.

14 Entity types (v0.3 ontology): `human`, `agent`, `llm`, `skill`, `tool`, `dataset`, `workflow`, `organization`, `community`, `compute_node`, `verifier_node`, `reviewer_node`, `sponsor`, `protocol_treasury`.

Each Entity may bind a **NodeProfile** and expose capabilities. See [ENTITY-SCHEMA-v0.3.md](./protocol/ENTITY-SCHEMA-v0.3.md) and [ENTITY-NODE-MANIFEST-v0.1.md](./protocol/ENTITY-NODE-MANIFEST-v0.1.md).

---

## Decentralization principle

PoCP’s end state is **no single mandatory platform server**. The network still needs bootstrap, relay, indexer, verifier, and compute nodes — but **anyone can run them**; they execute protocol rules, they do not own the protocol.

```text
Bitcoin needs nodes, not a central bank.
IPFS needs storage nodes, not a central CDN.
PoCP needs Entity Nodes, not a central AI platform.
```

---

## Internal economy (measure first)

| Unit | Meaning |
|------|---------|
| **CP** | Contribution Points |
| **AIC** | AI Credits — capability invocation |
| **CC** | Compute Credits — GPU/CPU time |
| **PT** | Protocol internal unit — stake / governance (future) |

**Tokenized measurement ≠ immediate public token issuance.**

**Default cycle:** quote → invoke → receipt → wallet → discovery rank.

**Optional contribution cycle:** contribute → CP → AIC/CC → reputation graph (not required per invoke).

---

## Minimum living network

Before scaling globally, the **exchange spine** must work on real nodes:

```text
Provider Node → discover capability → quote → invoke → receipt → wallet settlement
```

**Optional contribution closure** (witness path):

```text
→ Proof → AI verify → Human review → CP → Reputation → Event log
```

Details: [MINIMUM-LIVING-NETWORK.md](./MINIMUM-LIVING-NETWORK.md).

---

## Repository strategy (PoCP-Labs)

| Repo | Role |
|------|------|
| `pocp-protocol-spec` | Normative specs (future split) |
| `pocp-node` | Node runtime (future) |
| **`pocp-ai-commons`** | **Reference app + Phase A kernel** |
| `pocp-sdk-python` / `pocp-sdk-js` | Client SDKs (future) |
| `pocp-verifier-node` | Standalone verifier (future) |
| `pocp-reputation-indexer` | Graph indexer (future) |

Open: protocol, reference code, SDK, examples. Never open: keys, production secrets, raw user data.

---

## Execution phases

| Phase | Focus |
|-------|--------|
| **A** (now) | Entity + capability registry, invocation ledger, proof, settlement, local federation |
| **B** | Public nodes, discovery, multi-node compute/MCP |
| **C** | P2P discovery, DID-native events, reputation indexer, governance PIPs |

Roadmap: [ROADMAP-THREE-PHASES.md](./ROADMAP-THREE-PHASES.md). Agent Studio backlog: [agent-studio/CAPABILITY-INTERNET-BACKLOG.md](./agent-studio/CAPABILITY-INTERNET-BACKLOG.md). **PR sequence:** [UPGRADE-ROADMAP-PR-PLAN.md](./UPGRADE-ROADMAP-PR-PLAN.md).

---

## One sentence

**Do not build another AI platform — build the protocol layer for the AI capability internet.**
