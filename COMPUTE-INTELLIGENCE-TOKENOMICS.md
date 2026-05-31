# Compute & Intelligence Tokenomics

## Purpose

This document defines how PoCP measures and rewards compute and intelligence.

PoCP is not only a contribution ledger. It is a protocol network where compute and intelligence can be registered, invoked, verified, settled, and governed.

## Compute Measurement

Compute may be measured by:

- GPU seconds;
- GPU memory GB-hour;
- CPU seconds;
- memory GB-hour;
- storage GB-day;
- bandwidth GB;
- inference tokens;
- training steps;
- model serving uptime;
- vector search requests;
- verification computation.

## Compute Reward Formula

```text
Compute Reward =
Base Compute Unit
× Hardware Coefficient
× Availability Coefficient
× Performance Coefficient
× Verification Coefficient
× Reputation Coefficient
- Penalty
```

## Compute Verification

Early verification:

- requester confirmation;
- logs;
- output validation;
- random recomputation;
- redundant execution;
- benchmark reports.

Future verification:

- TEE;
- ZK proof;
- proof of inference;
- proof of training;
- challenge-response;
- benchmark attestation.

## Intelligence Measurement

Intelligence may be measured by:

- reasoning unit;
- skill invocation;
- agent task completion;
- review unit;
- knowledge contribution;
- workflow completion;
- human judgment;
- code contribution;
- documentation contribution;
- data contribution;
- research contribution.

## Intelligence Reward Formula

```text
Intelligence Reward =
Base Task Value
× Quality Score
× Difficulty Coefficient
× Impact Coefficient
× Originality Coefficient
× Human Review Coefficient
× Reuse Coefficient
× Reputation Coefficient
- Risk Penalty
```

## Intelligence Verification

Verification may include:

- AI verifier initial review;
- multi-model consensus;
- human reviewer final decision;
- evidence link;
- acceptance criteria;
- user feedback;
- result reuse;
- long-term outcome review.

## Compute vs Intelligence

Compute is easier to meter but harder to prove in adversarial networks.

Intelligence is harder to meter and requires human judgment.

PoCP must support both.

## Settlement Examples

### Code Review Task

- Human creator earns CP and AIC.
- Agent earns reputation and internal reward.
- Skill earns usage reputation.
- LLM provider records invocation.
- Human Reviewer earns review reputation and reward.

### Model Inference Task

- requester burns AIC and CC;
- compute node earns CC or PT;
- LLM provider earns AIC or PT;
- verifier earns verification reward;
- task output updates contribution graph.

## Principle

Paying for compute is not the same as rewarding contribution.

PoCP must distinguish resource supply, intelligence output, verified contribution, reputation, and governance power.

PoCP begins with contribution.
