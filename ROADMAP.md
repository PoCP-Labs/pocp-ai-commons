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

## Phase 3 — Pilot

Goal: Run a small real-world pilot.

Target users:

- Students
- Early developers
- Open-source contributors
- Public-good volunteers
- Community builders

Pilot size:

```text
30–100 users
10–30 contribution tasks
50–200 contribution events
```

Metrics:

- How many users return after first use?
- Do AI Credits motivate real contribution?
- Do human reviewers find AI verification useful?
- Are CP and Credits perceived as fair?
- Are there signs of abuse or gaming?
- Does AI access help users contribute more?

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
