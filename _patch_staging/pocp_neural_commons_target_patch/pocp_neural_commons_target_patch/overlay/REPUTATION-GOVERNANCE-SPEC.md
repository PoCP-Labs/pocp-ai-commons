# Reputation & Governance Spec

## Purpose

Reputation and governance decide who is trusted and who can influence protocol rules.

PoCP governance must not be token-only.

## Reputation Types

```text
Human Reputation
Agent Reputation
Skill Reputation
LLM Reliability
Tool Reliability
Dataset Trust
Workflow Success Rate
Compute Node Reliability
Verifier Accuracy
Reviewer Accuracy
Organization Trust
Sponsor Reliability
```

## Contextual Reputation

Reputation must be contextual.

Examples:

- A Human may be trusted for documentation, but not for security review.
- A Skill may be strong in translation, but weak in coding.
- A Compute Node may be reliable for inference, but not training.
- A Reviewer may be accurate in education tasks, but not legal tasks.

## Reputation Updates

Reputation may update from approved contribution, rejected contribution, successful invocation, failed invocation, review accuracy, challenge result, dispute result, long-term reuse, and abuse detection.

## Governance Objects

Governance may cover reward parameters, routing policy, verifier requirements, reviewer qualification, staking rules, slashing rules, sponsor pool rules, treasury allocation, external API access, and protocol upgrades.

## Governance Power

Suggested formula:

```text
Governance Power =
Token Stake
× Reputation Coefficient
× Recent Contribution Coefficient
× Role Eligibility
× Risk Adjustment
```

## Role Eligibility

Different proposals may require different eligible voters.

Examples:

- compute rules: compute node operators + reviewers + governance contributors;
- skill rules: skill builders + users + reviewers;
- verifier rules: verifier contributors + reviewers;
- treasury rules: governance members + sponsors + high-reputation contributors.

## AI Governance Assistant

AI can assist by summarizing proposals, identifying risks, comparing options, simulating effects, detecting conflicts, and drafting reports.

AI cannot finalize governance.

## Principle

Token can support governance.

Token must not dominate governance.

Contribution and reputation must matter.

PoCP begins with contribution.
