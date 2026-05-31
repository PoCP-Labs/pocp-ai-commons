# Gensyn → PoCP Mapping

**Status:** evaluating · **Registry slug:** `gensyn`

Gensyn focuses on **decentralized AI training, verification, and evolution**. PoCP treats training as **one contribution type**, not the whole network.

---

## Borrow

| Gensyn concept | PoCP mapping |
|----------------|--------------|
| Training job attestation | `ComputeReceipt` + witness plugins |
| Verifier network | `multi_verifier.py` external verifier slot |
| Training-as-work | `contribution_type: training` + submit validation + SubmitFlow UI |

---

## Reject

| Pattern | Reason |
|---------|--------|
| On-chain training market as default loop | Sprint Alpha off-chain credits |
| Replacing Contribution Graph with training graph only | PoCP multi-entity spine |

---

## Relation to compute adapters

Training jobs use the same **contribution-bound job** rules as [COMPUTE-ADAPTER-SPEC.md](../COMPUTE-ADAPTER-SPEC.md).

Schema: [TRAINING-CONTRIBUTION-SPEC.md](../TRAINING-CONTRIBUTION-SPEC.md) · `backend/config/schemas/training_contribution_v0.1.yaml`

Gensyn-specific attestation fields live under `receipt.integrity.training_attestation` — implemented in `compute_adapters/gensyn.py` stub.
