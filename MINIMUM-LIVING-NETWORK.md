# Minimum Living Network

## Purpose

The minimum living network proves that PoCP can evolve from an AI Commons app into a capability network.

## Nodes

```text
Node A: Human / Agent Node
Node B: Public Skill Node
Node C: Verifier / Reviewer Node
```

## First Capability

```text
code_review
```

## Required Flow

```text
1. Skill Entity registers a NodeProfile.
2. Skill Node publishes code_review Capability.
3. Agent discovers the Capability.
4. Agent creates Invocation.
5. Skill Node produces output_hash.
6. Skill Node submits Proof.
7. Verifier performs AI advisory verification.
8. Settlement distributes CP / AIC.
9. TokenAccount updates.
10. Reputation updates.
11. ProtocolEvent log records each step.
```

## Success Criteria

```text
Capability can be discovered.
Invocation can be created.
Proof requires invocation_id.
Settlement requires approved verification.
TokenAccount updates.
Reputation updates.
Protocol events are emitted.
```
