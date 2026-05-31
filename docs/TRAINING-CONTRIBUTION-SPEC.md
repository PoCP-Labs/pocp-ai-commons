# Training Contribution Spec v0.1 (draft)

**Gensyn-aligned training work as a PoCP contribution type — attestation without token-market spine.**

See also: [COMPUTE-ADAPTER-SPEC.md](./COMPUTE-ADAPTER-SPEC.md) · [inspiration-mappings/gensyn.md](./inspiration-mappings/gensyn.md) · [NO-TOKEN-FIRST.md](../NO-TOKEN-FIRST.md)

Schema file: [backend/config/schemas/training_contribution_v0.1.yaml](../backend/config/schemas/training_contribution_v0.1.yaml)

---

## 1. Why a separate type

Distributed AI infrastructure (Gensyn, federated training stacks) treats **training jobs as verifiable work**. PoCP already has:

- `ComputeReceipt` for execution attribution
- `multi_verifier` for external witness plugins
- Contribution-bound compute jobs

Training extends this with **dataset + model + checkpoint + metric** evidence — not a replacement for the Contribution Graph.

---

## 2. Contribution type

| Field | Value |
|-------|-------|
| `contribution_type` | `training` (draft — register in evidence standard v0.2) |
| Primary capability | `training` |
| Compute binding | `contribution_id` or `task_id` required on compute jobs |
| Receipt capability | `training` on `ComputeReceipt` |

---

## 3. Evidence envelope

Minimum `_pocp` + `training` block:

```json
{
  "_pocp": {
    "evidence_standard": "pocp.training_contribution.v0.1",
    "tags": ["training", "fine_tune"]
  },
  "training": {
    "job_id": "train-001",
    "objective": "fine_tune_study_agent",
    "dataset_ref": "dataset:pocp-entity-dataset-xyz",
    "model_ref": "huggingface:org/model",
    "metrics": { "loss_final": 0.42 },
    "verifier_reports": [
      { "verifier": "external-training-verifier", "passed": true, "score": 0.91 }
    ]
  }
}
```

---

## 4. ComputeReceipt extension

Under `integrity.training_attestation` (planned):

```json
{
  "capability": "training",
  "adapter": "gensyn-stub",
  "extra": {
    "resource_units": { "gpu_seconds": 3600, "gpu_count": 4 },
    "integrity": {
      "training_attestation": {
        "checkpoint_hash": "sha256:…",
        "verifier_entity_id": "pocp-entity-verifier-1"
      }
    }
  }
}
```

External network settlement (Gensyn token, etc.) → `extra.currency_note` only.

---

## 5. Witness flow

```text
Submit training contribution evidence
  → Schedule training compute job (contribution-bound)
  → External verifier plugin (multi_verifier slot)
  → Human / policy finalization
  → CP / AI Credits / reputation + graph edge
```

**Never:** job complete → auto-approve.

---

## 6. Borrow vs reject (Gensyn)

| Borrow | Reject |
|--------|--------|
| Training as verifiable work unit | On-chain training marketplace as PoCP default |
| Verifier network pattern | Replacing Contribution Graph |
| Checkpoint / metric attestation | Token as CP substitute |

---

## 7. Implementation checklist

```text
[x] Schema draft YAML
[x] Spec doc (this file)
[x] contribution_type=training validation on submit (contribution_submit.py)
[x] compute_adapters/gensyn stub (training capability)
[x] Proof layer training_attestation summary in compute_attribution
[x] EXTERNAL-INTEGRATIONS cross-link
```

---

## 8. One-line summary

> **Training is a contribution shape with attestation fields — not a separate token economy.**
