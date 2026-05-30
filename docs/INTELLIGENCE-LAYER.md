# PoCP Intelligence Capability Layer

PoCP is not only an LLM API wrapper. Over time it builds a **contribution intelligence layer** — native engines that understand, verify, match, and record contribution relationships.

See also: [Core Technology Stack](./CORE-TECH-STACK.md) · [Sprint Alpha](./SPRINT_ALPHA.md)

## Nine Capability Modules

| Module | Role | Current status |
|--------|------|----------------|
| Contribution Verification Engine | Assess contribution authenticity and value | Partial — `services/verifiers/*`, `routers/verification.py` |
| Entity Reputation Engine | Compute Human / Agent / Skill reputation | Partial — reputation on approval, federation import |
| Skill / Agent Matching Engine | Recommend suitable capabilities for tasks | Planned |
| CP / AI Credits Recommendation Engine | Suggest rewards from verified contribution | Partial — verifier consensus + Clarion-0 advisory |
| Anti-Abuse & Risk Engine | Limit gaming, self-approval, and duplicate evidence | Partial — `services/anti_abuse.py` |
| Contribution Graph Engine | Build the relationship graph of contribution | Partial — `services/graph.py`, graph API |
| Human Review Assistant | Support human reviewers with advisory packets | Partial — `services/clarion.py`, Clarion-0 endpoint |
| Governance Assistant | Summarize issues, risks, and policy options | Planned |
| External Intelligence API | Expose contribution intelligence to third parties | Skeleton — proof, portable entity, federation node APIs |

## Principle

> **AI is a witness, not a ruler.**

All intelligence modules produce **advisory output**. Final approval, governance, and rights issuance remain with accountable humans.

## Sprint Alpha Scope

Sprint Alpha wires the first living loop through a subset of this layer:

```text
Login → Wallet → AI Chat (Credits burn) → Contribution → AI Verify → Human Review → CP/Credits → Ledger
```

Do not add token, DAO, blockchain, or payment logic while stabilizing this loop.

## Long-Term Direction

The intelligence layer is what lets PoCP evolve from a single application into a **Contribution OS** kernel — a protocol layer where contribution events, entities, verification, reputation, and rights conversion are first-class objects other communities can reuse.
