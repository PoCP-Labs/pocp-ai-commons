# Cursor Prompt: Apply PoCP Neural Commons Network Architecture

You are working in `PoCP-Labs/pocp-ai-commons`.

A full Neural Commons Network architecture patch has been applied.

## Strategic direction

Reposition the project as:

> PoCP Neural Commons Network — a protocol-based distributed intelligence and compute network powered by verified contribution, tokenized measurement, capability routing, settlement, and entity reputation.

Keep:

> PoCP AI Commons as the first application scenario of the network.

## Your tasks

### 1. Update README.md

Use `README-NEURAL-COMMONS.md` as the source for the new first-screen positioning.

Do not delete existing Quick Start, Docker, smoke test, backend/frontend instructions.

Add a clear section:

```markdown
## PoCP AI Commons

PoCP AI Commons is the first application scenario of PoCP Neural Commons Network.

It starts with the first living loop:

Contribution → Verification → CP → AI Credits → AI Use → More Contribution.
```

### 2. Add architecture links

Add:

```markdown
## Neural Commons Architecture

- [Master Plan](NEURAL-COMMONS-MASTER-PLAN.md)
- [Roadmap](NEURAL-COMMONS-ROADMAP.md)
- [PR Plan](NEURAL-COMMONS-PR-PLAN.md)
- [Entity Registry](docs/architecture/01-ENTITY-REGISTRY.md)
- [Capability Registry](docs/architecture/02-CAPABILITY-REGISTRY.md)
- [Neural Routing](docs/architecture/03-NEURAL-ROUTING.md)
- [Invocation Ledger](docs/architecture/04-INVOCATION-LEDGER.md)
- [Verification & Proof](docs/architecture/05-VERIFICATION-PROOF.md)
- [Token Measurement](docs/architecture/06-TOKEN-MEASUREMENT.md)
- [Settlement Layer](docs/architecture/07-SETTLEMENT-LAYER.md)
- [Reputation & Governance](docs/architecture/08-REPUTATION-GOVERNANCE.md)
- [Neural Graph](docs/architecture/09-NEURAL-GRAPH.md)
```

### 3. Keep token language careful

Use:

```text
Tokenized measurement does not mean immediate public token issuance.
```

Do not promise token rewards, investment return, future airdrops, or financial gain.

### 4. Preserve open-source core boundary

The public repo may include:

- schemas;
- reference implementations;
- basic routing;
- basic token accounting;
- basic settlement;
- basic compute adapter interface.

Do not include:

- advanced anti-abuse weights;
- commercial neural routing optimizer;
- managed compute scheduler;
- enterprise private deployment logic;
- private risk model parameters.

### 5. Backend skeletons

The patch includes basic service skeletons. Ensure they import cleanly if integrated.

Do not force integration into existing routers unless safe.

### 6. Suggested next PR sequence

1. README + architecture docs.
2. Entity and Capability schemas.
3. Token Measurement internal accounting.
4. Invocation Ledger.
5. Settlement Layer.
6. Neural Routing basic service.
7. Compute Node basic adapter.
8. Reputation + Graph.

### 7. Suggested commit

```text
Add PoCP Neural Commons Network architecture
```
