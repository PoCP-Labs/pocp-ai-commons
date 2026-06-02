# Invocation Ledger

## Purpose

The Invocation Ledger records capability usage.

## Invocation Types

- Agent invocation
- LLM invocation
- Skill invocation
- Tool invocation
- Dataset access
- Workflow run
- Compute usage
- Verifier run
- Reviewer action

## Core Fields

```text
invocation_id
task_id
caller_entity_id
callee_entity_id
capability_id
input_hash
output_hash
cost_unit
cost_amount
status
started_at
completed_at
metadata
```
