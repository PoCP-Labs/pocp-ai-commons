# Neural Commons Integration Guide

## Purpose

This guide explains how to integrate the target architecture into the existing `pocp-ai-commons` codebase.

## Integration Strategy

The strategic target is direct:

> PoCP Neural Commons Network

The implementation should still be reviewed through PR batches.

## Existing Platform Role

Current `pocp-ai-commons` already has:

- Entity
- Contribution
- AI Verification
- Human Review
- Wallet
- CP
- AI Credits
- Ledger
- Agent / Skill / LLM Entity
- Smoke Test

These become the first nucleus of the Neural Commons Network.

## New Concepts to Add

- Compute Node
- Capability Registry
- Invocation Ledger
- Compute Credits
- Internal PoCP Token Account
- Settlement Layer
- Stake / Slashing
- Neural Routing
- Treasury / Sponsor Pool
- Reputation Governance

## Important Language

Use:

```text
Tokenized measurement
Internal protocol accounting units
Future protocol token
```

Avoid:

```text
Immediate public token issuance
Investment return
Token reward promise
```

## Implementation Order

1. Strategic docs and README positioning
2. Core models
3. Token measurement
4. Capability registry
5. Neural routing
6. Invocation ledger
7. Settlement flow
8. Graph explorer

PoCP begins with contribution.
