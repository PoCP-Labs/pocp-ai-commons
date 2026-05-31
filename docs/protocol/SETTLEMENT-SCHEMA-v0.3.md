# Settlement Schema v0.3

```json
{
  "settlement_id": "settle_001",
  "task_id": "task_001",
  "contribution_id": "contribution_001",
  "status": "pending | settled | disputed | reversed | slashed",
  "participants": [
    {
      "entity_id": "human_001",
      "role": "creator",
      "unit": "CP",
      "amount": 30,
      "reason": "Approved contribution"
    }
  ],
  "treasury_fee": 0,
  "sponsor_pool_id": null,
  "metadata": {}
}
```
