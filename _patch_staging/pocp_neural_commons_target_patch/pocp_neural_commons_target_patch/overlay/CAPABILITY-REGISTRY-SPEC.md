# Capability Registry Spec

## Purpose

The Capability Registry records what each Entity can do.

PoCP should not only register entities. It must register capabilities that can be invoked, priced, verified, reviewed, and settled.

## Capability Types

```text
reasoning
coding
translation
review
teaching
research
data_processing
workflow_execution
tool_call
dataset_access
gpu_inference
gpu_training
cpu_processing
storage
bandwidth
verification
human_judgment
governance
```

## Capability Object

Suggested fields:

```json
{
  "capability_id": "cap_001",
  "entity_id": "entity_001",
  "capability_type": "coding",
  "name": "Code Review Skill",
  "description": "Reviews Python code and suggests improvements.",
  "unit": "skill_invocation",
  "price_model": "fixed | dynamic | auction | sponsored",
  "base_price": 5,
  "accepted_units": ["AIC", "CC", "PT"],
  "verification_method": "human_review | ai_review | benchmark | log | tee | zk",
  "availability": "available | limited | offline",
  "reputation_score": 0,
  "risk_level": "low | medium | high",
  "metadata": {}
}
```

## Capability Units

```text
skill_invocation
agent_run
llm_token
reasoning_unit
review_unit
workflow_run
gpu_second
cpu_second
storage_gb_day
bandwidth_gb
dataset_query
tool_call
```

## Invocation Eligibility

Capability invocation may depend on price, availability, reputation, user balance, task type, role, governance rules, risk level, and compliance restrictions.

## Capability Reputation

Capability reputation should be contextual.

Examples:

- Code Review Skill has high reputation in Python code review.
- Translation Skill has high reputation in Chinese-English business translation.
- Compute Node has high reliability for inference, but low reliability for training.

## Capability Search

The registry should support search by type, unit, cost, reputation, availability, verification method, supported task type, owner, and risk level.

## Capability Lifecycle

```text
draft
→ registered
→ active
→ under_review
→ suspended
→ deprecated
→ archived
```

## Principle

Capability is the bridge between Entity and Task.

PoCP begins with contribution.
