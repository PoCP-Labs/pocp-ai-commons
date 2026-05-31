# PoCP Neural Commons Network

**Earn AI access through verified contribution.**  
**通过真实贡献，获得 AI 使用权。**

**PoCP Neural Commons Network** is a protocol-based distributed intelligence and compute network powered by verified contribution, tokenized measurement, and entity reputation.

It connects humans, agents, LLMs, skills, tools, datasets, workflows, compute nodes, and organizations into a verifiable contribution network.

Through CP, AI Credits, Compute Credits, and future protocol tokens, PoCP measures contribution, coordinates capability invocation, settles value, and builds entity reputation.

**PoCP AI Commons** is the first open-source application scenario of this network — the first practical loop of the **Proof of Contribution Protocol (PoCP)**.

## PoCP AI Commons

PoCP AI Commons is the first application scenario of PoCP Neural Commons Network.

It starts with the first living loop:

```text
Contribution → Verification → CP → AI Credits → AI Use → More Contribution
```

The network target expands this into capability matching, neural routing, invocation, settlement, and reputation — see [Neural Commons Architecture](#neural-commons-architecture) below.

**Execution path:** we ship in three phases — **Phase A** (demonstrable public loop, ~80% done) → **Phase B** (operable distributed network) → **Phase C** (contribution internet). See [docs/ROADMAP-THREE-PHASES.md](./docs/ROADMAP-THREE-PHASES.md).

---

> If AI becomes a basic productive capability, how can ordinary people gain fair access to it through real contribution?

PoCP AI Commons is not just another AI chat platform.

It is a contribution-based AI capability network where humans, agents, skills, models, tools, datasets, workflows, and organizations can participate in tasks, generate contribution records, receive verification, build reputation, and earn AI access.

**Tokenized measurement does not mean immediate public token issuance.** In early versions, CP, AI Credits, Compute Credits, and PoCP Token accounts may be implemented as internal protocol accounting units. External issuance, transferability, staking, and governance must be designed separately with legal, security, and governance review.

---

## Core Idea

In most AI platforms, the relationship is simple:

```text
User pays → User uses AI
```

PoCP AI Commons proposes a different loop:

```text
User contributes
    ↓
Contribution is verified
    ↓
User earns CP and AI Credits
    ↓
User uses AI
    ↓
AI helps user contribute more
```

This is the first practical loop of PoCP:

```text
Contribution → Verification → CP → AI Credits → AI Use → More Contribution
```

---

## Why This Matters

AI is becoming a basic capability.

But access to powerful AI tools is still shaped by money, language, geography, education, and platform control.

PoCP AI Commons explores another path:

* basic AI capability for everyone;
* more AI access through verified contribution;
* reputation built from real contribution;
* human review over algorithmic authority;
* transparent contribution ledger;
* future governance based on contribution, not capital.

---

## What Is PoCP?

**PoCP**, or **Proof of Contribution Protocol**, is a contribution proof protocol for humans and intelligent agents in the age of AI.

It records and verifies contributions from humans, AI agents, LLMs, skills, tools, datasets, workflows, organizations, and communities.

PoCP does not ask only *who owns what?* It asks:

> Who contributed what?  
> Who verified it?  
> Who benefited from it?  
> What rights should follow from it?

---

## First MVP

The first MVP focuses on one demonstrable loop:

```text
User registers
    ↓
User receives basic AI Credits
    ↓
User completes a contribution task
    ↓
AI verifier gives advisory review
    ↓
Human reviewer confirms
    ↓
User earns CP and AI Credits
    ↓
Contribution is recorded in the ledger
```

**MVP modules:** user identity · AI Credits wallet · AI tools · task center · contribution submission · AI advisory review · human review · contribution ledger · entity reputation.

---

## Intelligent Entities

The platform is built around **Entities** — not only human users.

An Entity can be: Human · Agent · LLM · Skill · Tool · Dataset · Workflow · Organization · Community.

The first MVP focuses on **Human + Agent + Skill**. A contribution may be created by a human, assisted by an agent, powered by a skill, verified by AI witnesses, and finalized traceably under entity-equal policy.

---

## AI Is a Witness, Not a Ruler

AI verifiers assist in contribution review — task match, quality, originality, impact, risk, evidence credibility, suggested CP and AI Credits.

**AI cannot hold hidden authority.** Finalization is policy-automated and traceable — witness quorum + delegate (any Entity type). See [docs/ENTITY-EQUALITY.md](./docs/ENTITY-EQUALITY.md).

---

## What PoCP AI Commons Is Not

* a token-first crypto project;
* another generic AI chatbot;
* a social credit system;
* a platform for extracting free labor;
* an AI-controlled governance system;
* a promise of unlimited free AI usage.

The first version does not issue a token. It focuses on:

```text
Contribution → Verification → AI Credits → Reputation → Ledger
```

See [NO-TOKEN-FIRST.md](./NO-TOKEN-FIRST.md).

---

## Neural Commons Architecture

Target architecture for the distributed intelligence and compute network (PoCP AI Commons remains the first application):

### Master plan & execution

| Document | Purpose |
|----------|---------|
| [NEURAL-COMMONS-MASTER-PLAN.md](./NEURAL-COMMONS-MASTER-PLAN.md) | Master plan and network layers |
| [NEURAL-COMMONS-ROADMAP.md](./NEURAL-COMMONS-ROADMAP.md) | Roadmap and milestones |
| [NEURAL-COMMONS-PR-PLAN.md](./NEURAL-COMMONS-PR-PLAN.md) | Suggested PR breakdown |
| [README-NEURAL-COMMONS.md](./README-NEURAL-COMMONS.md) | Neural Commons README companion |

### Architecture modules (9 layers)

| Document | Purpose |
|----------|---------|
| [01 — Entity Registry](./docs/architecture/01-ENTITY-REGISTRY.md) | Entity registry and identity |
| [02 — Capability Registry](./docs/architecture/02-CAPABILITY-REGISTRY.md) | Capability registration and discovery |
| [03 — Neural Routing](./docs/architecture/03-NEURAL-ROUTING.md) | Neural routing and matching |
| [04 — Invocation Ledger](./docs/architecture/04-INVOCATION-LEDGER.md) | Invocation ledger and receipts |
| [05 — Verification & Proof](./docs/architecture/05-VERIFICATION-PROOF.md) | Verification and proof packets |
| [06 — Token Measurement](./docs/architecture/06-TOKEN-MEASUREMENT.md) | CP, AI Credits, Compute Credits accounting |
| [07 — Settlement Layer](./docs/architecture/07-SETTLEMENT-LAYER.md) | Settlement and attribution |
| [08 — Reputation & Governance](./docs/architecture/08-REPUTATION-GOVERNANCE.md) | Reputation and governance |
| [09 — Neural Graph](./docs/architecture/09-NEURAL-GRAPH.md) | Neural graph and network topology |

### Network specs & integration

| Document | Purpose |
|----------|---------|
| [POCP-NEURAL-COMMONS-NETWORK.md](./POCP-NEURAL-COMMONS-NETWORK.md) | Network overview and layers |
| [TOKEN-MEASUREMENT-LAYER.md](./TOKEN-MEASUREMENT-LAYER.md) | CP, AI Credits, Compute Credits, protocol token accounting |
| [COMPUTE-INTELLIGENCE-TOKENOMICS.md](./COMPUTE-INTELLIGENCE-TOKENOMICS.md) | Compute and intelligence value flow |
| [CAPABILITY-REGISTRY-SPEC.md](./CAPABILITY-REGISTRY-SPEC.md) | Capability registry and invocation |
| [COMPUTE-NODE-SPEC.md](./COMPUTE-NODE-SPEC.md) | Compute node profiles and receipts |
| [NEURAL-ROUTING-SPEC.md](./NEURAL-ROUTING-SPEC.md) | Neural routing and matching |
| [SETTLEMENT-LAYER-SPEC.md](./SETTLEMENT-LAYER-SPEC.md) | Settlement and attribution |
| [REPUTATION-GOVERNANCE-SPEC.md](./REPUTATION-GOVERNANCE-SPEC.md) | Reputation and governance |
| [PR-PLAN-NEURAL-COMMONS.md](./PR-PLAN-NEURAL-COMMONS.md) | Earlier PR plan (superseded by NEURAL-COMMONS-PR-PLAN) |
| [docs/NEURAL-COMMONS-INTEGRATION-GUIDE.md](./docs/NEURAL-COMMONS-INTEGRATION-GUIDE.md) | Integration guide |
| [docs/NEURAL-COMMONS-GLOSSARY.md](./docs/NEURAL-COMMONS-GLOSSARY.md) | Terminology |
| [docs/implementation/CURSOR-NEURAL-COMMONS-EXECUTION.md](./docs/implementation/CURSOR-NEURAL-COMMONS-EXECUTION.md) | Cursor execution checklist |
| [docs/implementation/MIGRATION-FROM-AI-COMMONS.md](./docs/implementation/MIGRATION-FROM-AI-COMMONS.md) | Migration from AI Commons MVP |

---

## Open Core Strategy

PoCP follows an **Open Core** model.

The protocol specifications, reference implementation, SDKs, and community tools are open source.

Advanced anti-abuse intelligence, commercial neural routing, enterprise governance, managed compute scheduling, commercial API gateway, private deployment tooling, and advanced reputation / risk models may be provided under separate commercial terms.

| Document | Purpose |
|----------|---------|
| [OPEN-CORE.md](./OPEN-CORE.md) | Open Core strategy overview |
| [LICENSE-POLICY.md](./LICENSE-POLICY.md) | Licensing recommendations |
| [COMMERCIAL.md](./COMMERCIAL.md) | Commercial boundary |
| [SECURITY.md](./SECURITY.md) | Security policy and reporting |
| [DATA-CONSENT.md](./DATA-CONSENT.md) | Data consent |
| [ANTI-ABUSE-POLICY.md](./ANTI-ABUSE-POLICY.md) | Anti-abuse policy |
| [REPOSITORY-BOUNDARY.md](./REPOSITORY-BOUNDARY.md) | Repository split boundaries |
| [OPEN-SOURCE-ROADMAP.md](./OPEN-SOURCE-ROADMAP.md) | Open-source roadmap |
| [COMMERCIAL-MODULES.md](./COMMERCIAL-MODULES.md) | Commercial module planning |
| [docs/OPEN-CORE-INTEGRATION-GUIDE.md](./docs/OPEN-CORE-INTEGRATION-GUIDE.md) | Integration guide |

---

## Public Open-Source Core

PoCP keeps its protocol skeleton, schemas, reference implementation, SDK-facing interfaces, and community tools open source.

The public repository is intended to remain readable, runnable, auditable, and contributor-friendly.

Commercial intelligence capabilities — including advanced anti-abuse intelligence, commercial neural routing, managed compute scheduling, enterprise governance, private deployment tooling, and advanced reputation / risk models — may be implemented in separate commercial modules.

| Document | Purpose |
|----------|---------|
| [OPEN-SOURCE-CORE-QUALITY.md](./OPEN-SOURCE-CORE-QUALITY.md) | Public core quality standards |
| [REFERENCE-IMPLEMENTATION.md](./REFERENCE-IMPLEMENTATION.md) | Reference implementation scope |
| [PUBLIC-CORE-BOUNDARY.md](./PUBLIC-CORE-BOUNDARY.md) | What stays public |
| [COMMERCIAL-RESERVED-BOUNDARY.md](./COMMERCIAL-RESERVED-BOUNDARY.md) | What remains commercial |
| [REPO-HEALTH-CHECKLIST.md](./REPO-HEALTH-CHECKLIST.md) | Repository health checklist |
| [CONTRIBUTOR-QUALITY-GUIDE.md](./CONTRIBUTOR-QUALITY-GUIDE.md) | Contributor quality guide |
| [docs/FORMATTER-AND-CI-GUIDE.md](./docs/FORMATTER-AND-CI-GUIDE.md) | Formatter and CI setup |

Some architecture documents describe the target modular structure. The current reference implementation may still use aggregated routers or services while modularization is in progress.

**Repository health check:** `python backend/scripts/health_check.py`

---

## Genesis Package

These four documents are the project's genesis block:

| Document | Purpose |
|----------|---------|
| [GENESIS.md](./GENESIS.md) | Why PoCP is a new species for the AI age |
| [AI-COMMONS.md](./AI-COMMONS.md) | First application: the AI commons network |
| [PROTOCOL-SPEC-v0.1.md](./PROTOCOL-SPEC-v0.1.md) | Minimal protocol spec for implementation |
| [docs/README.md](./docs/README.md) | Full documentation index |

**Genesis translations:** [中文](docs/genesis/zh-CN.md) · [Français](docs/genesis/fr.md) · [Deutsch](docs/genesis/de.md) · [العربية](docs/genesis/ar.md) · [Русский](docs/genesis/ru.md)

---

## Roadmap

| Phase | Focus |
|-------|--------|
| **0 — Genesis** | README, Genesis, AI Commons, Protocol spec, repo setup |
| **1 — MVP** | Login, wallet, AI chat, tasks, submission, AI review, human review, ledger |
| **2 — Pilot** | 30–100 early users, verified tasks, anti-abuse testing |
| **3 — Contribution Graph** | Human + Agent + Skill records, reputation, graph explorer |
| **4 — Protocol Expansion** | Decentralized verification, on-chain anchoring, governance by contribution |

Details: [ROADMAP.md](./ROADMAP.md)

---

## Guiding Principles

1. Contribution before speculation.
2. AI access through verified contribution.
3. AI is advisory; humans make final decisions.
4. Reputation must be earned, not bought.
5. Verification must not become surveillance.
6. Contributors should share in the value they help create.
7. Humans, agents, and skills can contribute, but human responsibility remains essential.

---

## Quick Start

```bash
docker compose up --build
```

| Service | URL |
|---------|-----|
| Frontend dashboard | http://localhost:3000 |
| API health | http://localhost:8000/health |
| API docs | http://localhost:8000/docs |

**Demo:** First boot seeds genesis entities and the R-language study scenario with one completed verify → approve loop.

**Smoke test:**

```bash
cd backend && python scripts/smoke_test.py
```

**Optional rich demo seed** (partners, inspirations, bundled capabilities):

```bash
POCP_FULL_SEED=true docker compose up --build
```

See [docs/LOCAL-SETUP.md](./docs/LOCAL-SETUP.md) for dev login, verifiers, and SQLite mode.

---

## Development Status

PoCP AI Commons is in **Genesis MVP** stage.

The current goal is to prove one loop end-to-end:

```text
A person completes a contribution task
→ multi-witness AI advisory review
→ policy auto-finalize (traceable Entity + policy id)
→ system issues CP and AI Credits
→ contribution enters ledger + graph Merkle proof
```

---

## Community

| Document | Purpose |
|----------|---------|
| [CONTRIBUTING.md](./CONTRIBUTING.md) | How to contribute |
| [GOVERNANCE.md](./GOVERNANCE.md) | Human review and community decisions |
| [GOOD_FIRST_ISSUES.md](./GOOD_FIRST_ISSUES.md) | Starter tasks for new contributors |
| [AI-CREDITS-CP-REPUTATION.md](./AI-CREDITS-CP-REPUTATION.md) | CP, AI Credits, and reputation model |

---

## Related

* [PoCP Manifesto](https://github.com/PoCP-Labs/pocp-manifesto)
* [PoCP Labs](https://github.com/PoCP-Labs)

---

## License

MIT License — see [LICENSE](./LICENSE).

---

## Final Line

**Contribution is the proof. AI access is the right.**  
**贡献即凭证，AI 即公共能力。**
