# Akash / Render → PoCP Mapping

**Status:** evaluating · **Registry slugs:** `akash`, `render-network`  
**Compute spec:** [COMPUTE-ADAPTER-SPEC.md](../COMPUTE-ADAPTER-SPEC.md)

---

## Role in PoCP stack

Akash and Render are **compute marketplace benchmarks** — PoCP uses them as **external Compute Entity sources**, not as settlement spine.

```text
Akash/Render  =  where GPU runs
PoCP          =  why it ran (contribution), who gets credit, proof + ledger
```

---

## Borrow

| Upstream pattern | PoCP target |
|------------------|-------------|
| Provider registration | `compute_profile` + Compute Entity |
| Job deployment / lease | `compute_scheduler.submit` with `contribution_id` |
| Resource metering | `ComputeReceipt.resource_units` |
| Marketplace discovery | `GET /compute/providers` + community partner registry |

---

## Reject

| Pattern | Reason |
|---------|--------|
| Native token as PoCP currency | NO-TOKEN-FIRST |
| Job success → auto-approve contribution | Human/policy finalization |
| Rebuilding full DePIN network inside PoCP | Adapter-only per COMPUTE-ADAPTER-SPEC |

---

## Implementation path

1. `backend/services/compute_adapters/base.py` — interface
2. Stub adapters for Akash + Render manifests
3. Partner outreach: log via `POST /community-partners/partners/{slug}/outreach`
4. Proof: attach receipt to contribution evidence before finalization
