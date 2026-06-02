# Invocation Ledger Spec

Invocation defines what actually happened when one Entity called another Entity's Capability.

```json
{
  "invocation_id": "invoke_001",
  "task_id": "task_001",
  "caller_entity_id": "agent_001",
  "callee_entity_id": "skill_001",
  "capability_id": "cap_code_review",
  "input_hash": "sha256:input",
  "output_hash": "sha256:output",
  "cost_unit": "AIC",
  "cost_amount": 5,
  "status": "completed"
}
```

## Status Machine

```text
created → accepted → running → completed → proof_submitted → verified → settled
```
