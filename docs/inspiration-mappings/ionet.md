# io.net → PoCP Mapping

**Status:** evaluating · **Registry slug:** `io-net`  
**Compute spec:** [COMPUTE-ADAPTER-SPEC.md](../COMPUTE-ADAPTER-SPEC.md)

---

## Industry position

io.net positions itself as a **decentralized GPU network** supplying scalable compute for machine learning — same infrastructure tier as Akash/Render, not the training-verification layer of Gensyn.

---

## Borrow

| io.net pattern | PoCP target |
|----------------|-------------|
| GPU cluster provider | `POST /compute/adapters/io-net/import` |
| ML job units | `ComputeReceipt.resource_units.gpu_seconds` / `gpu_count` |
| Training + inference jobs | contribution-bound adapter jobs (`capability`: `llm_inference` or `training`) |

**Code:** `backend/services/compute_adapters/ionet.py` (stub)

---

## Reject

| Pattern | Reason |
|---------|--------|
| IO token as PoCP currency | NO-TOKEN-FIRST |
| DePIN mining market inside PoCP | Adapter-only |
| Job success → auto-finalize | Human/policy gate |

---

## Relation to Gensyn

- **io.net** = GPU supply (adapter layer)
- **Gensyn** = training/verification attestation ([TRAINING-CONTRIBUTION-SPEC.md](../TRAINING-CONTRIBUTION-SPEC.md))

A training contribution may use io.net GPU receipts **and** Gensyn-style verifier reports in the same proof packet.
