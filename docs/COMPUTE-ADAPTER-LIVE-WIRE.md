# Compute Adapter Live Wire (draft)

**How to connect PoCP compute adapters to real Akash / Render / io.net / Gensyn APIs** without adopting their token settlement loops.

See also: [COMPUTE-ADAPTER-SPEC.md](./COMPUTE-ADAPTER-SPEC.md) · [TRAINING-CONTRIBUTION-SPEC.md](./TRAINING-CONTRIBUTION-SPEC.md) · [NO-TOKEN-FIRST.md](../NO-TOKEN-FIRST.md)

---

## 1. Principle

```text
External network     →  runs GPU / training job  →  returns job status + metrics
PoCP adapter         →  normalizes to ComputeReceipt  →  binds to contribution_id
PoCP settlement      →  human/policy finalization  →  CP / AI Credits (never AKT/RNDR/IO)
```

Live wire adds **HTTP clients** behind existing adapter methods. Stub behavior continues until `live_wire_active: true` in the adapter catalog.

---

## 2. Environment variables

| Adapter | Base URL | Auth token | Notes |
|---------|----------|------------|-------|
| `akash` | `POCP_AKASH_API_URL` | `POCP_AKASH_API_TOKEN` | Provider REST / GraphQL gateway |
| `render-network` | `POCP_RENDER_API_URL` | `POCP_RENDER_API_TOKEN` | Job API |
| `io-net` | `POCP_IONET_API_URL` | `POCP_IONET_API_TOKEN` | Cluster job API |
| `gensyn` | `POCP_GENSYN_API_URL` | `POCP_GENSYN_API_TOKEN` | Training attestation API |

Optional shared settings:

```bash
POCP_ADAPTER_HTTP_TIMEOUT=120
POCP_ADAPTER_LIVE_ENABLED=false   # master switch when wire clients ship
```

When `POCP_*_API_URL` is set **and** `POCP_ADAPTER_LIVE_ENABLED=true`, Akash jobs call the gateway (Phase 1). Other adapters remain stub until their wire clients ship.

---

## 3. PoCP Akash Gateway API v0.1 (operator contract)

PoCP nodes do not embed Akash SDK directly in Sprint Alpha. Operators run a **thin gateway** that maps:

```text
PoCP adapter HTTP  →  gateway  →  Akash deployment API
```

### POST `{POCP_AKASH_API_URL}/v1/deployments`

Request:

```json
{
  "capability": "llm_inference",
  "contribution_id": "uuid",
  "task_id": "uuid",
  "requester_entity_id": "entity-id",
  "provider_entity_id": "pocp-adapt-akash-eco",
  "constraints": {
    "image": "ghcr.io/org/infer:latest",
    "cpu_units": 1,
    "memory": "1Gi",
    "gpu_units": 1
  }
}
```

Response:

```json
{
  "deployment_id": "dseq-12345",
  "status": "pending"
}
```

### GET `{POCP_AKASH_API_URL}/v1/deployments/{deployment_id}`

Response (running):

```json
{ "deployment_id": "dseq-12345", "status": "activating" }
```

Response (success):

```json
{
  "deployment_id": "dseq-12345",
  "status": "active",
  "gpu_seconds": 42.5,
  "output_preview": "…",
  "external_settlement_ref": "optional-akt-tx-evidence-only"
}
```

Status mapping in `backend/services/compute_adapters/akash_live.py`.

Client: `backend/services/compute_adapters/akash_live.py` · HTTP: `live_http.py`

---

## 4. Akash live wire (deployment lifecycle)

### PoCP → Akash

| Step | PoCP call | External mapping |
|------|-----------|------------------|
| Import | `POST /compute/adapters/akash/import` | Store `deployment_template`, `owner_address` in entity metadata |
| Submit | `submit_job(spec)` | Create deployment / lease with env vars from `constraints` |
| Poll | `poll_job(external_job_id)` | Query deployment status (active / closed) |
| Receipt | `build_receipt(result)` | Map `gpu_seconds`, deployment id, optional `akt_tx` as **metadata only** |

### Required `constraints` (live)

```json
{
  "sdl_version": "2.0",
  "cpu_units": 1,
  "memory": "1Gi",
  "gpu_units": 1,
  "image": "ghcr.io/org/inference:latest",
  "env": { "MODEL": "llama3.2" }
}
```

### Receipt extension

```json
{
  "adapter": "akash",
  "external_job_id": "dseq-12345",
  "resource_units": {
    "gpu_seconds": 42.5,
    "network": "akash"
  },
  "integrity": {
    "external_settlement_ref": "akt-tx-optional-evidence-only"
  }
}
```

**Reject:** Using `akt_tx` as PoCP CP mint trigger.

---

## 4. io.net live wire (phase 1)

| Step | Mapping |
|------|---------|
| Submit | POST cluster job with `contribution_id` in job labels |
| Poll | GET job status + GPU hours |
| Receipt | `resource_units.gpu_seconds`, `cluster_id` |

Training-capable jobs use same contribution-bound rules as inference.

---

## 5. Gensyn live wire (training only)

Gensyn adapter **only** accepts `capability: training`.

| Step | Mapping |
|------|---------|
| Submit | Register training work unit with `objective`, `dataset_ref`, `model_ref` from contribution evidence |
| Poll | Fetch verifier reports + checkpoint hashes |
| Receipt | `integrity.training_attestation` (required) |

Align evidence with `pocp.training_contribution.v0.1`:

```json
{
  "integrity": {
    "training_attestation": {
      "objective": "fine_tune_study_agent",
      "checkpoint_hash": "sha256:…",
      "verifier_passed": true,
      "verifier_score": 0.91
    }
  }
}
```

**Reject:** On-chain training market completion auto-finalizing PoCP contributions.

---

## 6. Error surface

Adapters map external failures to federation-safe errors:

| Code | Meaning |
|------|---------|
| `adapter_unavailable` | Network timeout / 5xx |
| `job_not_found` | Stale external_job_id |
| `capability_mismatch` | e.g. gensyn + llm_inference |
| `contribution_unbound` | Missing contribution_id and task_id |

Never leak provider API keys in error messages or proof packets.

---

## 7. Implementation phases

```text
Phase 0 (today)   Stub adapters + live_config env detection
Phase 1           Akash HTTP client (deploy + status)
Phase 2           io.net + Render job clients
Phase 3           Gensyn training attestation client
Phase 4           Optional TEE attestation block (TrustlessInference pattern)
```

Checklist tracks in [COMPUTE-ADAPTER-SPEC.md](./COMPUTE-ADAPTER-SPEC.md) §9.

---

## 8. Verification

1. Set `POCP_AKASH_API_URL` → catalog shows `live_configured: true`
2. Submit contribution-bound job → `external_job_id` from real network (phase 1+)
3. Poll until succeeded → `ComputeReceipt` in proof packet
4. `POST /api/v1/proof/verify` includes compute attribution layer
5. Contribution remains **pending** until human/policy finalization

Tests: `backend/tests/test_compute_adapters.py` · `backend/tests/test_compute_adapter_live_config.py`
