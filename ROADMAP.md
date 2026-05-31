# PoCP AI Commons Roadmap

PoCP AI Commons is the first open-source application of the Proof of Contribution Protocol.

Its larger direction is the **Contribution Internet for the AI era**:

```text
PC Internet      → information becomes connected
Mobile Internet  → people and services become connected
PoCP             → contribution relationships become connected and verifiable
```

Its first goal is to prove one living loop:

```text
Contribution → Verification → CP → AI Credits → AI Use → More Contribution
```

For the protocol-architecture evolution that sits underneath these phases, see [docs/ARCHITECTURE-EVOLUTION.md](./docs/ARCHITECTURE-EVOLUTION.md).

For **Epic tracking** (contribution network → optional token path), see [docs/TOKEN-PATHWAY-EPICS.md](./docs/TOKEN-PATHWAY-EPICS.md).

## Phase 0 — Genesis

Goal: Define the project and make it understandable.

Status: Complete.

Deliverables:

- README
- GENESIS.md
- AI-COMMONS.md
- PROTOCOL-SPEC-v0.1.md
- Community launch docs
- Genesis contributor records
- Initial backend and frontend prototype

## Phase 1 — Genesis MVP

Goal: Run the first working contribution loop.

Status: Complete (demo seed, verify → approve loop, ledger, graph).

Core features:

- Entity model
  - Human
  - Agent
  - Skill
  - Organization
  - LLM provider
- Task center
- Contribution submission
- AI advisory verification
- Human review
- CP issuance
- AI Credits issuance
- Wallet
- Ledger
- Reputation
- Contribution Graph

Success condition:

> A user completes a contribution task, receives AI verification, gets human approval, earns CP and AI Credits, and sees the contribution in the ledger.

## Phase 2 — Sprint Alpha

Goal: Turn the demo into a real usable MVP.

Status: In progress.

Core features:

- GitHub OAuth or dev login
- Auto-create Human Entity
- Starter AI Credits
- OpenAI Verifier
- DeepSeek Verifier
- Mock Verifier fallback
- Multi-verifier aggregation
- AI Chat that burns AI Credits
- AI usage logs
- Minimal anti-abuse:
  - Evidence required
  - Daily contribution limit
  - Daily AI Credits burn limit
  - Self-approval blocked

Success condition:

> A real user can log in, receive AI Credits, use AI Chat, contribute, receive verification, earn more Credits, and continue using AI.

## Phase 3 — Pilot (Three-Layer Entity Network)

Goal: Prove the **protocol + distributed compute + distributed intelligence** stack with a small real network — not merely a human signup count.

See [docs/INTELLECTUAL-EQUALITY.md](./docs/INTELLECTUAL-EQUALITY.md) · [docs/DISTRIBUTED-LAYERS.md](./docs/DISTRIBUTED-LAYERS.md) · [docs/PILOT-LAUNCH-CHECKLIST.md](./docs/PILOT-LAUNCH-CHECKLIST.md).

Target participants (Entity types):

- Human Entities — students, developers, reviewers, sponsors
- Agent Entities — StudyAgent and community agents
- Skill Entities — imported or bundled skills
- LLM Witness Entities — Lumen-0, DeSui, local Ollama, peer witnesses
- Optional: Organization, Tool, Dataset Entities

Pilot scale (three-layer metrics):

```text
≥30 active Entities (across ≥4 entity types)
10–30 contribution tasks
50–200 approved contribution events
≥50 exportable Contribution Proof Packets
≥30 InvocationTrace records (avg chain depth ≥3: Human→Agent→Skill→LLM)
≥2 compute/witness providers (e.g. local Ollama + 1 peer or vLLM node)
≥1 cross-node proof import (Epic D — when second operator ready)
≥3 distinct finalizer Entities (any type — Human, Agent, LLM, …)
```

Metrics:

- Active Entity count and type diversity (not human registrations alone)
- Return rate: Entities with 2+ contribution-related events in 7 days
- Proof packet export and (optional) federation import success
- Witness quorum coverage (local + remote adapters)
- Do AI Credits motivate real contribution?
- Are CP and Credits perceived as fair?
- Abuse and gaming signals
- Does distributed witness compute reduce single-vendor dependency?

Success condition:

> A multi-Entity contribution network runs end-to-end: distributed witness compute, intelligence orchestration, portable proof, ledger + graph Merkle memory, and visible graph relationships — with traceable policy finalization, not a privileged human gate.

## Phase 4 — Contribution Graph

Goal: Make the intelligent contribution graph visible.

This is the moment where PoCP begins to look less like a single app and more like a network. The product should show how humans, Agents, Skills, tools, reviewers, sponsors, and contributions connect.

Core features:

- Entity pages
- Human profile
- Agent profile
- Skill profile
- Contribution event graph
- Invocation chain
- Reputation view
- Ledger explorer

Success condition:

> Users can see how humans, agents, skills, tools, and reviewers jointly created verified contributions.

## Phase 5 — Skill and Agent Commons

Goal: Let reusable Skills and Agents become first-class contribution entities.

Core features:

- Skill registry
- Agent registry
- Skill reputation
- Agent reputation
- Skill invocation logs
- Agent task performance history
- Skill contribution attribution

Success condition:

> A Skill or Agent can accumulate reputation through verified task participation.

## Phase 6 — Governance by Contribution

Goal: Introduce limited governance based on contribution.

Initial governance areas:

- Task category priorities
- CP/Credits conversion parameters
- Reviewer selection
- Anti-abuse rules
- Skill quality standards

Principle:

> Governance should follow living contribution, not passive ownership.

## Phase 7 — Protocol Expansion

Goal: Make PoCP usable beyond the first application.

At this phase, PoCP should become a protocol layer other communities can use to record and verify contribution relationships.

Possible directions:

- API for third-party contribution verification
- External task communities
- Sponsor pools
- AI capability distribution reports
- Contribution graph export
- On-chain hash anchoring
- Decentralized verification experiments

Not first:

- Token issuance
- Trading
- Financial speculation
- Full DAO governance

PoCP begins with contribution.
