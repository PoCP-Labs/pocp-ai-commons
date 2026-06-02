# Cursor Prompt: Apply PoCP Neural Commons Target Architecture Patch

You are working in `PoCP-Labs/pocp-ai-commons`.

## Strategic target

Reposition the project as:

**PoCP Neural Commons Network** — a protocol-based distributed intelligence and compute network powered by verified contribution, tokenized measurement, and entity reputation.

PoCP AI Commons remains the first application scenario.

## README update

Use `README-NEURAL-COMMONS-REWRITE.md` as the source for the new positioning, but preserve useful Quick Start, API, demo, and smoke test instructions.

The README should say:

```text
PoCP Neural Commons Network is a protocol-based distributed intelligence and compute network.

It connects humans, agents, LLMs, skills, tools, datasets, workflows, compute nodes, and organizations into a verifiable contribution network.

Through CP, AI Credits, Compute Credits, and future protocol tokens, PoCP measures contribution, coordinates capability invocation, settles value, and builds entity reputation.

PoCP AI Commons is the first application scenario of this network.
```

## Add architecture links

Add a README section:

```markdown
## Neural Commons Architecture

- [PoCP Neural Commons Network](POCP-NEURAL-COMMONS-NETWORK.md)
- [Token Measurement Layer](TOKEN-MEASUREMENT-LAYER.md)
- [Compute & Intelligence Tokenomics](COMPUTE-INTELLIGENCE-TOKENOMICS.md)
- [Capability Registry Spec](CAPABILITY-REGISTRY-SPEC.md)
- [Compute Node Spec](COMPUTE-NODE-SPEC.md)
- [Neural Routing Spec](NEURAL-ROUTING-SPEC.md)
- [Settlement Layer Spec](SETTLEMENT-LAYER-SPEC.md)
- [Reputation & Governance Spec](REPUTATION-GOVERNANCE-SPEC.md)
- [Neural Commons PR Plan](PR-PLAN-NEURAL-COMMONS.md)
```

## Protocol note

If `PROTOCOL-SPEC-v0.2.md` exists, add a short section named `Neural Commons Target Architecture`.

If only `PROTOCOL-SPEC-v0.1.md` exists, add a forward-looking note.

## Important wording

Use:

```text
Tokenized measurement does not mean immediate public token issuance.

In early versions, CP, AI Credits, Compute Credits, and PoCP Token accounts may be implemented as internal protocol accounting units. External issuance, transferability, staking, and governance must be designed separately with legal, security, and governance review.
```

## Do not

- Do not promise token rewards.
- Do not add public token issuance logic.
- Do not break existing backend/frontend demo.
- Do not remove smoke tests.
- Do not rewrite the entire codebase in one PR.

## Suggested commit

`Add PoCP Neural Commons target architecture`
