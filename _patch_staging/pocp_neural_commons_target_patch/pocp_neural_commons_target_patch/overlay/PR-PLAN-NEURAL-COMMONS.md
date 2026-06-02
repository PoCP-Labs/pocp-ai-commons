# PR Plan — PoCP Neural Commons Network

This plan executes the target architecture in clear PR batches.

The target architecture is decided upfront.

Implementation should still be done through separate PRs for safety and reviewability.

## PR 1 — Strategic Repositioning

### Title

```text
Reposition project as PoCP Neural Commons Network
```

### Includes

- README target positioning
- Neural Commons architecture docs
- Token Measurement docs
- Capability Registry docs
- Settlement docs
- Reputation Governance docs

### Purpose

Move the project from AI Credits app framing to the target distributed intelligence and compute network framing.

## PR 2 — Core Model Refactor

### Title

```text
Add Neural Commons core models
```

### Includes

- expanded EntityType
- ComputeNode
- VerifierNode
- ReviewerNode
- Sponsor
- ProtocolTreasury
- Capability model
- Invocation model
- TokenAccount model
- SettlementRecord model
- StakeRecord model
- ReputationRecord model

## PR 3 — Token Measurement Layer

### Title

```text
Add token measurement accounting layer
```

### Includes

- CP / AIC / CC / PT internal units
- TokenAccount service
- CreditTransaction extension
- token ledger
- treasury flow skeleton
- sponsor pool skeleton

## PR 4 — Capability Registry

### Title

```text
Add capability registry and capability search
```

### Includes

- capability registration
- capability unit
- price model
- verification method
- capability reputation
- capability search API

## PR 5 — Neural Routing Service

### Title

```text
Add neural routing service skeleton
```

### Includes

- task analyzer
- capability matcher
- execution planner
- cost estimator
- risk estimator
- rule-based routing MVP

## PR 6 — Invocation & Execution Ledger

### Title

```text
Add invocation and execution ledger
```

### Includes

- Agent invocation
- Skill invocation
- LLM invocation
- Tool invocation
- Compute invocation
- input/output hash
- execution cost
- success/failure status

## PR 7 — Verification & Settlement Flow

### Title

```text
Connect verification, review, settlement, and reputation
```

### Includes

- verify invocation result
- verify compute usage
- human review
- settlement distribution
- token / credit allocation
- reputation update
- ledger record

## PR 8 — Neural Graph Explorer

### Title

```text
Build Neural Commons graph explorer
```

### Includes

- Entity graph
- Capability graph
- Invocation graph
- Contribution graph
- Settlement graph
- Reputation graph

## Rules

- Do not put everything in one PR.
- Preserve existing Genesis demo where possible.
- Keep AI advisory and accountable review.
- Make tokenized measurement explicit but do not promise public token issuance.
- Add tests or smoke test steps for each PR.

PoCP begins with contribution.
