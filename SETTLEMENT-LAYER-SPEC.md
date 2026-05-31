# Settlement Layer Spec

## Purpose

The Settlement Layer distributes value after a task, invocation, contribution, or verification event.

It answers:

> Who should receive what, why, and based on what proof?

## Settlement Inputs

Settlement may depend on task budget, contribution event, invocation records, compute usage, AI usage, verification result, human review, reputation, risk, stake, sponsor rules, and treasury rules.

## Settlement Participants

A settlement may include human creator, task requester, agent executor, skill provider, LLM provider, tool provider, dataset provider, workflow provider, compute node, AI verifier, human reviewer, organization, sponsor pool, and protocol treasury.

## Settlement Units

Settlement may use CP, AI Credits, Compute Credits, internal PoCP token units, and future external PoCP protocol tokens.

## Settlement Record

Suggested fields:

```json
{
  "settlement_id": "settle_001",
  "task_id": "task_001",
  "contribution_id": "contribution_001",
  "status": "pending | settled | disputed | reversed",
  "participants": [
    {
      "entity_id": "human_001",
      "role": "creator",
      "unit": "CP",
      "amount": 30,
      "reason": "Approved contribution"
    },
    {
      "entity_id": "skill_001",
      "role": "skill_provider",
      "unit": "AIC",
      "amount": 10,
      "reason": "Effective skill invocation"
    }
  ],
  "treasury_fee": 0,
  "sponsor_pool_id": null,
  "created_at": "datetime"
}
```

## Settlement Status

```text
pending
verified
settled
disputed
reversed
slashed
expired
```

## Dispute and Appeal

Settlement should support challenge, dispute, appeal, reviewer escalation, evidence update, and settlement revision.

## Slashing

Slashing may apply to fake compute node, malicious verifier, collusive reviewer, spam agent, fraudulent evidence, and repeated abuse.

## Treasury

The protocol treasury may receive protocol fees, sponsor deposits, unused credits, slashing proceeds, grants, and ecosystem funding.

Treasury may spend on public-good AI credits, compute subsidies, verifier rewards, developer grants, community operations, and security audits.

## Principle

Settlement must be explainable.

PoCP begins with contribution.
