# Settlement Schema v0.3

PoCP settlement runs **after** upstream resources are invoked (MCP tools, GPU jobs, training attestation). External network tokens are evidence only — not PoCP CP issuance currency.

See also: [CAPABILITY-SCHEMA-v0.3.md](./CAPABILITY-SCHEMA-v0.3.md) · [TRAINING-CONTRIBUTION-SPEC.md](../TRAINING-CONTRIBUTION-SPEC.md) · [COMPUTE-ADAPTER-SPEC.md](../COMPUTE-ADAPTER-SPEC.md)

---

## Settlement layers (proof packet)

| Layer | Source | Role |
|-------|--------|------|
| `provenance` | OCTP envelope | How work was created |
| `mcp_invocation_context` | MCP invoke | Tool steps + capability receipt hashes |
| `compute_attribution` | ComputeReceipt | GPU / training resource units |
| `training` evidence | `contribution_type: training` | Job id, dataset, model, metrics |
| `ledger` | Human/policy finalization | CP / AI Credits mint |

---

## Core settlement record

```json
{
  "settlement_id": "settle_001",
  "task_id": "task_001",
  "contribution_id": "contribution_001",
  "contribution_type": "knowledge | training | code | …",
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
  "metadata": {
    "finalizer_entity_id": "pocp-entity-clarion-0",
    "proof_layers": ["provenance", "mcp_invocation_context", "compute_attribution"]
  }
}
```

---

## Training settlement extension

Training contributions add compute adapter attestation without auto-finalizing on job complete.

```json
{
  "settlement_id": "settle_train_001",
  "contribution_id": "contrib_train_001",
  "contribution_type": "training",
  "status": "pending",
  "metadata": {
    "evidence_standard": "pocp.training_contribution.v0.1",
    "compute_adapter": "gensyn",
    "external_job_id": "gensyn-stub-abc123",
    "integrity": {
      "training_attestation": {
        "objective": "fine_tune_study_agent",
        "verifier_passed": true
      }
    },
    "finalization": {
      "auto_on_job_complete": false,
      "requires_human_or_policy": true
    }
  }
}
```
