# Compute Adapter Spec v0.1 (draft)

**External decentralized compute networks as PoCP Compute Entities — not a PoCP-operated GPU cloud.**

See also: [DISTRIBUTED-COMPUTE-RESEARCH.md](./DISTRIBUTED-COMPUTE-RESEARCH.md) · [ENTITY-MARKET-SPEC.md](./ENTITY-MARKET-SPEC.md) · [DISTRIBUTED-INTELLIGENCE-BENCHMARK.md](./DISTRIBUTED-INTELLIGENCE-BENCHMARK.md) · [NO-TOKEN-FIRST.md](../NO-TOKEN-FIRST.md)

---

## 1. Problem

Projects like **Akash**, **Render**, **io.net**, **Aethir**, and **Nosana** solve:

```text
GPU/CPU supply  ↔  job marketplace  ↔  provider payout (often token-based)
```

PoCP does **not** rebuild that marketplace. PoCP needs:

```text
Who ran compute for which Contribution?
Was the job contribution-bound?
What receipt proves execution?
How does reputation enter the graph?
How do AI Credits / settlement flow bilaterally between Entities?
```

This spec defines a **thin adapter** between external compute networks and PoCP's existing modules.

---

## 2. Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│ PoCP Protocol (non-negotiable)                              │
│ Contribution · Proof · Human finalization · Ledger          │
└───────────────────────────▲─────────────────────────────────┘
                            │
┌───────────────────────────┴─────────────────────────────────┐
│ PoCP Compute Layer (today)                                  │
│ compute_profile · compute_scheduler · compute_executor      │
│ compute_receipt · compute_attribution · peer_compute          │
└───────────────────────────▲─────────────────────────────────┘
                            │ Compute Adapter (this spec)
┌───────────────────────────┴─────────────────────────────────┐
│ External networks (examples)                                │
│ Akash · Render · Ollama · vLLM · peer nodes                 │
└─────────────────────────────────────────────────────────────┘
```

**Rule:** External network tokens are **never** PoCP's primary settlement loop. Adapters may record external tx ids as **evidence**, not as CP issuance.

---

## 3. Adapter contract

Each adapter implements:

| Method | Purpose |
|--------|---------|
| `register_provider(db, config)` | Create/update `Compute Node` Entity + `compute_profile` |
| `quote_job(job_spec)` | Optional cost/latency estimate (advisory) |
| `submit_job(job_spec)` | Dispatch to external network; return `external_job_id` |
| `poll_job(external_job_id)` | Status: queued / running / succeeded / failed |
| `build_receipt(result)` | Normalize to PoCP `ComputeReceipt` |
| `map_failure(error)` | Federation-safe error surface |

### Required job fields

Every adapter job **must** include:

| Field | Required | Notes |
|-------|----------|-------|
| `contribution_id` or `task_id` | Yes | Anti-abuse binding |
| `capability` | Yes | e.g. `llm_inference`, `embeddings`, `training` |
| `requester_entity_id` | Yes | Who pays / initiates |
| `provider_entity_id` | Yes | Local Compute Entity |
| `trace_id` | Recommended | Links to `InvocationTrace` |

### Receipt fields (minimum)

Align with `backend/services/compute_receipt.py`:

```json
{
  "provider": "akash-adapter",
  "external_job_id": "...",
  "capability": "llm_inference",
  "contribution_id": "...",
  "started_at": "...",
  "finished_at": "...",
  "resource_units": {},
  "integrity": {},
  "request_hash": "...",
  "response_hash": "..."
}
```

Optional: TEE attestation block (TrustlessInference pattern) under `integrity.tee_attestation`.

---

## 4. Entity model

External network → PoCP Entity:

| External concept | PoCP Entity |
|------------------|-------------|
| Akash provider / deployment | `compute` or `community` + `compute_profile` |
| Render GPU node | same |
| Ollama host (local) | `llm` / `compute` Entity (already active) |
| Peer witness node | federation peer + `peer_compute` |

Registry entries:

- `external_inspirations.yaml` — benchmark + borrow/declined policy
- `community_partners.yaml` — outreach partners (Akash, Render as prospects)
- `neural_network_sources.yaml` — adapter status (`adapter_planned`)

---

## 5. Target adapters (priority)

| Network | Status | PoCP module target | Borrow | Reject |
|---------|--------|-------------------|--------|--------|
| **Ollama** | **active** | `ollama_client.py`, verifiers | Local inference + embed | Token mining |
| **vLLM / llama.cpp** | **active** | community witness nodes | OpenAI-compatible API | Centralized-only gate |
| **Akash** | evaluating | `compute_adapters/akash.py` | Deployment lifecycle, resource metering | AKT as PoCP currency |
| **Render** | evaluating | `compute_adapters/render.py` | GPU job units | RNDR settlement loop |
| **io.net** | evaluating | `compute_adapters/ionet.py` | GPU cluster scaling | IO token settlement loop |
| **Gensyn** | evaluating | `compute_adapters/gensyn.py` | Training attestation stub | On-chain training market |

---

## 6. API surface (existing + planned)

| Method | Path | Today |
|--------|------|-------|
| GET | `/api/v1/compute/adapters` | Adapter catalog |
| POST | `/api/v1/compute/adapters/{slug}/import` | Register external provider Entity |
| POST | `/api/v1/compute/adapters/{slug}/jobs` | Submit contribution-bound adapter job |
| POST | `/api/v1/compute/adapters/{slug}/jobs/{job_id}/poll` | Poll + finalize ComputeReceipt |
| GET | `/api/v1/contributions/{id}/compute-jobs` | Jobs bound to a contribution |

Live wire: [COMPUTE-ADAPTER-LIVE-WIRE.md](./COMPUTE-ADAPTER-LIVE-WIRE.md) · env `POCP_*_API_URL` sets `live_configured` on catalog.

Planned:

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/v1/compute/adapters/{slug}/import` | Register external provider manifest |
| GET | `/api/v1/compute/adapters` | List evaluating/active adapters |

---

## 7. Graph and proof integration

After job completion:

1. Append `ComputeReceipt` to contribution evidence
2. Graph edge: `provides_compute` (provider → contribution hub)
3. Proof layer: `compute_attribution_context` (existing pattern)
4. Ledger event: optional `compute_job_settled` (off-chain credits only in Sprint Alpha)

Reputation updates follow **approved contributions**, not raw GPU hours.

---

## 8. Policy constraints

From [NO-TOKEN-FIRST.md](../NO-TOKEN-FIRST.md) and [ENTITY-MARKET-SPEC.md](./ENTITY-MARKET-SPEC.md):

- ❌ Anonymous miner markets (Bittensor-style)
- ❌ Adapter auto-finalizes contributions on job success
- ❌ Mandatory chain wallet for operators
- ✅ Bilateral Entity settlement with portable Proof
- ✅ External network payout recorded as optional metadata
- ✅ Human / policy finalization remains the gate

---

## 9. Implementation checklist

```text
[x] Adapter interface module: backend/services/compute_adapters/base.py
[x] Akash stub adapter: backend/services/compute_adapters/akash.py
[x] Render stub adapter: backend/services/compute_adapters/render.py
[x] API: GET /api/v1/compute/adapters
[x] API: POST /api/v1/compute/adapters/{slug}/import
[x] API: POST /api/v1/compute/adapters/{slug}/jobs
[x] API: POST /api/v1/compute/adapters/{slug}/jobs/{job_id}/poll
[x] Tests: backend/tests/test_compute_adapters.py
[x] Docs: EXTERNAL-INTEGRATIONS.md §27
[x] Live wire draft: docs/COMPUTE-ADAPTER-LIVE-WIRE.md
[x] Env detection: backend/services/compute_adapters/live_config.py
[x] Akash gateway HTTP client: backend/services/compute_adapters/akash_live.py
[ ] Operator-hosted Akash gateway reference implementation
[ ] io.net + Render live job clients
[ ] Gensyn training attestation client
```

Track in [DEV-TASKS.md](../DEV-TASKS.md) under Distributed Compute.

---

## 10. One-line summary

> **External GPU clouds sell capacity; PoCP adapters prove that capacity served a verified Contribution and record it in the graph and ledger.**
