# PoCP Architecture Evolution

PoCP should not jump directly from a Genesis prototype to a full protocol network architecture.

It should evolve by proving one protocol claim at a time.

That is the architectural discipline of PoCP:

```text
First prove a contribution rule.
Then stabilize the protocol object.
Then expand the system that hosts it.
```

PoCP is not a conventional SaaS product where architecture is mainly about scale, services, and deployment.

Its first architectural question is different:

```text
What must be true for contribution to become a first-class protocol object?
```

Only after that question is answered should PoCP widen into federation, governance, and wider value distribution.

See also: [GENESIS.md](../GENESIS.md), [PROTOCOL.md](./PROTOCOL.md), [ARCHITECTURE.md](./ARCHITECTURE.md), and [CORE-TECH-STACK.md](./CORE-TECH-STACK.md).

## Architectural Principle

PoCP evolves through protocol claims, not feature piles.

Each phase should prove one new statement about the network.

If a phase cannot clearly answer:

```text
What new property of verified contribution has now become real?
```

then the system has likely expanded faster than the protocol has matured.

## The Two Architecture Levels

PoCP must distinguish between two architecture levels.

### 1. Genesis Minimal Architecture

This is the smallest architecture that can prove the first living loop:

```text
Task
→ Contribution Event
→ Evidence
→ AI Advisory Verification
→ Human Review
→ CP / AI Credits / Reputation
→ Ledger Memory
→ Contribution Graph
```

Its purpose is not completeness.

Its purpose is to prove one thing only:

> Can real contribution be verified and converted into AI usage rights?

### 2. Full Protocol Architecture

This is the long-term architecture required for PoCP to function as a contribution network rather than a single application.

It eventually includes:

- portable proof packets;
- federation and proof import;
- layered rights;
- reputation and trust computation;
- reviewer governance;
- dispute handling;
- sponsor allocation and contribution-based resource routing.

The Genesis minimal architecture is a proof machine.

The full protocol architecture is a contribution civilization operating system.

PoCP must not confuse the two.

## Phase Model

PoCP architecture should evolve through five phases.

Each phase adds one new protocol property.

## Phase 0: Genesis Minimal Loop

### Protocol claim

Real contribution can be verified and converted into AI usage rights.

### Required architecture

- Entity identity for Human, Agent, Skill, and minimal LLM participation;
- task creation and task context;
- Contribution Event submission;
- evidence attachment and evidence hashing;
- AI advisory verification;
- accountable human final approval;
- CP and AI Credits issuance;
- ledger write;
- Contribution Graph projection.

### Success condition

One real contribution passes through the full loop:

```text
submit
→ verify
→ approve
→ rights conversion
→ ledger memory
```

### Architectural discipline

At this phase, architecture exists to prove the loop, not to maximize feature breadth.

### Failure mode

The system becomes a bundle of:

```text
task board + AI chat + points + graph UI
```

instead of a contribution proof system.

## Phase 1: Trusted Collaboration

### Protocol claim

Multi-entity collaboration can be attributed without collapsing into vague participation records.

### Required architecture

- stronger participant role semantics;
- invocation traces connecting Human, Agent, Skill, and LLM activity;
- role-specific evidence;
- clearer primary responsibility and reviewer responsibility boundaries;
- early anti-abuse and duplicate-claim detection.

### Success condition

The network can explain not only that a contribution happened, but also:

```text
which entities added value,
what role each entity played,
which roles are advisory,
and which human carried final accountability.
```

### Architectural discipline

Attribution must record increment, not mere presence.

Appearing in the workflow is not the same thing as earning contribution weight.

### Failure mode

Agents, Skills, reviewers, and sponsors are all attached to events, but no one can explain who actually created incremental value.

## Phase 2: Portable Proof and Federation

### Protocol claim

Contribution can leave the local database and remain a portable, verifiable proof object.

### Required architecture

- Contribution Proof Packet export;
- portable entity identity;
- ledger anchor and proof hash;
- federation node metadata;
- import and verification of external proofs;
- trust policy for imported reputation and proof acceptance.

### Success condition

Another PoCP node can inspect a contribution proof packet and verify that it is a real protocol object, not just an application snapshot.

### Architectural discipline

PoCP must export proof, not just data.

### Failure mode

Federation exists in name, but exported payloads are merely internal records with no durable proof semantics.

## Phase 3: Layered Rights Architecture

### Protocol claim

Verified contribution can generate more than a single reward balance.

### Required architecture

- clear separation of AI Credits, CP, and Reputation;
- conversion rules from contribution events into multiple rights layers;
- policy surfaces for access rights, reviewer eligibility, and future governance eligibility;
- early decay, trust weighting, or recency logic for reputation.

### Success condition

The network can clearly distinguish:

- AI Credits as usage rights;
- CP as contribution event accounting;
- Reputation as long-term trust and responsibility memory.

### Architectural discipline

Rights must not collapse into a single score.

### Failure mode

The system treats AI Credits, CP, and Reputation as three names for the same number.

## Phase 4: Contribution Governance and Resource Allocation

### Protocol claim

Contribution history can guide real decisions about review, sponsorship, resource allocation, and protocol governance.

### Required architecture

- reviewer governance and reviewer qualification rules;
- dispute resolution flows;
- sponsor resource allocation policies;
- community-level task publication and moderation;
- federated trust boundaries;
- anti-abuse adjudication and correction flows.

### Success condition

The network can route scarce AI capability, review authority, and sponsor resources through contribution-aware governance rather than passive ownership.

### Architectural discipline

Governance must follow living contribution, not speculative position.

### Failure mode

The system has governance surfaces, but no accountable human mechanisms and no defensible path from contribution to governance legitimacy.

## Cross-Phase Rule

PoCP should only widen architecture after the previous protocol claim has been made real.

This is the core sequence:

```text
Phase 0 proves the contribution loop.
Phase 1 proves collaborative attribution.
Phase 2 proves portability.
Phase 3 proves layered rights.
Phase 4 proves contribution-shaped governance.
```

Skipping a phase usually means one of two failures:

- the protocol remains underdefined while the system grows;
- the product grows while the contribution object stays weak.

## Current Position

PoCP AI Commons currently sits between Phase 0 and early Phase 1.

Already present:

- minimal contribution loop;
- dual AI advisory verification pattern;
- human approval requirement;
- wallet, CP, AI Credits, and reputation state;
- ledger memory and proof export surfaces;
- contribution graph and invocation traces;
- early federation surfaces.

Not yet fully stabilized:

- protocol-hard definition of Contribution Event as a responsibility-bearing claim;
- stricter participant attribution and role-specific evidence semantics;
- full rights layering beyond demo-level conversion;
- governance-grade dispute and reviewer institutions.

## What Should Be Built Next

The next architectural step should not be a jump to the full protocol architecture.

It should harden the Phase 0 to Phase 1 transition.

That means:

1. make Contribution Event semantics stricter;
2. tighten participant attribution and invocation-linked evidence;
3. separate advisory AI judgment from accountable human final responsibility even more clearly;
4. make contribution-to-rights conversion more protocol-shaped and less demo-shaped.

## One-Line Summary

PoCP should not scale by adding more features first.

It should scale by proving, one phase at a time, that verified contribution can become identity, rights, memory, coordination, and governance in the age of AI.