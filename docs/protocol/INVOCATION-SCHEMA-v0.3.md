# Invocation Schema v0.3

```json
{
  "invocation_id": "invoke_001",
  "task_id": "task_001",
  "caller_entity_id": "human_001",
  "callee_entity_id": "agent_001",
  "capability_id": "cap_001",
  "input_hash": "sha256:...",
  "output_hash": "sha256:...",
  "cost_unit": "AIC",
  "cost_amount": 5,
  "status": "pending | running | completed | failed | disputed",
  "metadata": {}
}
```
