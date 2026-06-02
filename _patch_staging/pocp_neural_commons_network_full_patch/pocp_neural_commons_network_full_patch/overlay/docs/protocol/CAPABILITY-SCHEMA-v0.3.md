# Capability Schema v0.3

```json
{
  "capability_id": "cap_001",
  "entity_id": "entity_001",
  "capability_type": "coding | reasoning | review | gpu_inference | tool_call",
  "name": "Code Review Capability",
  "unit": "skill_invocation | agent_run | llm_token | gpu_second",
  "price_model": "fixed | dynamic | auction | sponsored",
  "base_price": 5,
  "accepted_units": ["AIC", "CC", "PT"],
  "verification_method": "human_review | ai_review | benchmark | log | tee | zk",
  "availability": "available | limited | offline",
  "reputation_score": 0,
  "risk_level": "low",
  "metadata": {}
}
```
