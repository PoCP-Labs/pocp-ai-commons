# Token Measurement Layer

## Purpose

The Token Measurement Layer defines how PoCP measures contribution, intelligence usage, compute usage, settlement, staking, slashing, treasury flows, and governance weight.

Tokenized measurement is a protocol accounting design. It does not require immediate public token issuance.

## Four Value Units

```text
CP  = Contribution Points
AIC = AI Credits
CC  = Compute Credits
PT  = PoCP Protocol Token
```

## CP — Contribution Points

CP measures verified contribution.

Properties:

- contribution record;
- non-financial by default;
- may be non-transferable;
- used for reputation and eligibility;
- may influence AI Credits, Compute Credits, and future rights.

CP answers:

> How much verified contribution did this Entity create?

## AIC — AI Credits

AI Credits are usage rights for intelligence capabilities.

They may be used for AI Chat, LLM invocation, Agent invocation, Skill invocation, AI verifier usage, workflow execution, and intelligence assistance.

AIC answers:

> What intelligence capability can this Entity access?

## CC — Compute Credits

Compute Credits are usage rights for compute capabilities.

They may be used for GPU inference, GPU training, CPU processing, storage, bandwidth, vector search, model serving, and compute verification.

CC answers:

> What compute capability can this Entity access?

## PT — PoCP Protocol Token

PoCP Protocol Token is the future protocol-layer settlement, staking, and governance unit.

It may be used for cross-network settlement, verifier staking, compute node staking, slashing, governance, treasury flows, sponsor pools, protocol fees, and value return.

PT must not be the starting point of the system.

## Relationship

```text
Contribution → CP
CP → AI Credits / Compute Credits eligibility
AI Credits → Intelligence usage
Compute Credits → Compute usage
Usage → Invocation Ledger
Invocation → Contribution Event
Contribution Event → Verification
Verification → Settlement
Settlement → Reputation + Token/Credit Distribution
```

## Internal Token Accounts

Suggested account fields:

```text
entity_id
cp_balance
ai_credit_balance
compute_credit_balance
pocp_token_balance_internal
locked_balance
staked_balance
slashed_balance
pending_rewards
```

## Credit Transactions

Transaction types:

```text
grant
earn
burn
settle
stake
unstake
slash
refund
sponsor
treasury_in
treasury_out
adjustment
```

## Settlement Rule

Settlement should be multi-entity.

A single task may settle rewards to human creator, agent executor, skill provider, LLM provider, tool provider, dataset provider, compute node, verifier, human reviewer, organization, sponsor pool, and protocol treasury.

## Governance Weight

Governance must not be token-only.

Suggested formula:

```text
Governance Power =
Token Stake
× Reputation Coefficient
× Recent Contribution Coefficient
× Role Eligibility
× Risk Adjustment
```

## Transferability

Suggested early rules:

```text
CP: non-transferable
AIC: non-transferable or limited-transfer usage credit
CC: non-transferable or limited-transfer usage credit
PT: internal accounting first; external transfer later only after review
```

## Principle

Token can measure value.

Token cannot replace contribution.

Token cannot buy reputation directly.

PoCP begins with contribution.
