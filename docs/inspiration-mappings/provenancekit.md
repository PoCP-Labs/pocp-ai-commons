# ProvenanceKit (EAA) → PoCP Mapping

**Status:** evaluating · **Registry slug:** `provenancekit`  
**Source:** [Arttribute/provenancekit](https://github.com/Arttribute/provenancekit)

---

## Borrow

| EAA block | PoCP Proof extension |
|-----------|---------------------|
| Entity | PoCP Entity slice in proof packet |
| Action | InvocationStep / ContributionEvent |
| Attribution | Participant roles + CP split |
| `ext:witness` | Verifier outputs |
| `ext:ai` | LLM / agent steps |
| `ext:contrib` | Contribution metadata |

Target modules: `proof.py`, `provenance.py`, `compute_receipt.py`.

---

## Reject

- On-chain settlement as default
- EAA graph replacing Human finalization gate

---

## Deliverable (BI-3)

Export PoCP Proof Packet with optional EAA-compatible extension blocks for federation import.
