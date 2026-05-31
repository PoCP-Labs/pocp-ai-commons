# Compute Capacity & Artifact Spec v0.2 (draft)

**Time-window slot booking and content-addressed compute artifact cache — the «storage» layer of distributed compute.**

See also: [DISTRIBUTED-TOKEN-RESEARCH.md](./DISTRIBUTED-TOKEN-RESEARCH.md) · [COMPUTE-METERING-SPEC.md](./COMPUTE-METERING-SPEC.md) · [ENTITY-MARKET-SPEC.md](./ENTITY-MARKET-SPEC.md)

---

## 1. Problem

Raw compute (FLOPS, GPU cycles) **cannot be stored**. PoCP still needs:

| Need | Mechanism |
|------|-----------|
| Save earned value | Settlement Token in Wallet (AI Credits) |
| Reserve future compute | **Capacity reservation** — book provider slots |
| Avoid repeat GPU work | **ComputeArtifact** — cache outputs by input hash |

---

## 2. Capacity reservation

### 2.1 Model

```json
{
  "reservation_id": "uuid",
  "consumer_entity_id": "uuid",
  "provider_entity_id": "uuid",
  "capability": "llm_inference",
  "window_start": "2026-06-01T02:00:00Z",
  "window_end": "2026-06-01T04:00:00Z",
  "slots": 1,
  "prepaid_credits": 50.0,
  "contribution_id": "uuid",
  "status": "active | cancelled | fulfilled | expired"
}
```

**Analogy:** AWS Reserved Instance — not storing electricity, **booking generation capacity**.

### 2.2 API (v0.2 prototype — in-memory)

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/v1/compute/capacity/reservations` | Create reservation |
| GET | `/api/v1/compute/capacity/reservations` | List consumer reservations |
| DELETE | `/api/v1/compute/capacity/reservations/{id}` | Cancel |

**Rules:**

- Requires `contribution_id` or `task_id` (contribution-bound)
- `window_end > window_start`
- v0.2: prepaid credits recorded but **not yet debited** from Wallet (v0.3)
- Scheduler may prefer providers with active reservation for matching consumer

### 2.3 Future (v0.3)

- Debit Wallet on create; refund on cancel within policy
- Provider accepts/declines reservation
- Federation: mirror reservations across trusted nodes
- Conflict detection vs `max_concurrent` on ComputeProfile

---

## 3. ComputeArtifact cache

### 3.1 Model

Content-addressed store keyed by `(model, sha256(input_material))`:

```json
{
  "model": "qwen2.5:7b",
  "input_hash": "sha256...",
  "output_hash": "sha256...",
  "output_material": "...",
  "provider_entity_id": "uuid",
  "stored_at": "ISO8601"
}
```

### 3.2 Execution modes

| Mode | GPU used | Consumer charge | Provider credit |
|------|----------|-----------------|-----------------|
| `live_inference` | Yes | Full token rate | Full token rate |
| `cache_hit` | No | × `cache_hit_consumer_multiplier` (default 0.1) | × `cache_hit_provider_multiplier` (default 0.05) |

Receipt `extra`:

```json
{
  "execution_mode": "cache_hit",
  "usage": { "...": "..." },
  "artifact_ref": {
    "input_hash": "...",
    "output_hash": "...",
    "stored_at": "..."
  }
}
```

### 3.3 API

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/v1/compute/artifacts` | List cached artifacts (debug/operator) |

**Env:** `POCP_COMPUTE_ARTIFACT_CACHE=true` (default on)

### 3.4 Future (v0.3)

- Postgres / object store backend
- TTL and size limits per Entity
- Federation artifact import with signed manifest
- Embedding index as first-class Artifact type

---

## 4. Code map

| Component | Path |
|-----------|------|
| Capacity service | `backend/services/compute_capacity.py` |
| Artifact service | `backend/services/compute_artifact.py` |
| Metering (cache multipliers) | `backend/services/compute_metering.py` |
| Executor integration | `backend/services/compute_executor.py` |
| Routes | `backend/routers/compute.py` |

---

## 5. One line

> **Book capacity in time; cache artifacts in hash space; store value in Wallet.**
