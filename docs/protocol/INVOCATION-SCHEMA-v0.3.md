# Invocation Schema v0.3

PoCP records runtime chains as **InvocationTrace** + ordered **InvocationStep** rows, aligned with the [Entity Connection matrix](./ENTITY-CONNECTION.md).

Related: [CAPABILITY-SCHEMA-v0.3.md](./CAPABILITY-SCHEMA-v0.3.md) · [ENTITY-CONNECTION.md](./ENTITY-CONNECTION.md)

---

## Trace envelope

```json
{
  "invocation_id": "trace_uuid",
  "initiator_entity_id": "human_001",
  "task_id": "task_001",
  "contribution_id": "contrib_001",
  "model_provider": "deepseek",
  "status": "started | completed | failed",
  "steps": []
}
```

| Field | Notes |
|-------|--------|
| `initiator_entity_id` | Usually `human`; accountability anchor for the run |
| `contribution_id` | Optional link to Contribution Event (protocol layer) |
| `model_provider` | Advisory label for default LLM routing |

---

## Step (operational layer)

```json
{
  "step_order": 1,
  "source_entity_id": "human_001",
  "target_entity_id": "agent_001",
  "action": "uses",
  "metadata": {
    "capability_receipt": { "schema": "pocp.capability_receipt.v0.1" }
  }
}
```

### Canonical actions (type-pair matrix)

| Source type | Target type | `action` |
|-------------|-------------|----------|
| human | agent, skill, tool, workflow | `uses` |
| agent | skill | `calls` |
| agent | tool, workflow | `uses` |
| agent | llm | `invokes_llm` |
| skill | llm | `invokes_llm` |
| skill | tool | `calls` |
| tool | tool | `invokes_mcp` |
| tool | llm | `invokes_llm` |
| workflow | agent, skill | `calls` |
| workflow | tool | `uses` |
| compute_node | llm | `hosts_inference` |
| verifier_node | llm | `witnesses` |

Steps that violate the matrix are rejected when recorded via `record_invocation` (strict mode).

---

## Example — Pilot study chain

```
Human ──uses──► Agent ──calls──► Skill ──invokes_llm──► LLM
```

Each step may carry a **capability receipt** in `metadata` for proof export and federation.

---

## API

| Endpoint | Purpose |
|----------|---------|
| `POST /api/v1/invocations` | Record trace (legacy human→agent→skill path) |
| `GET /api/v1/entities/{id}/connections` | Instance operational + protocol + structural view |
| `GET /api/v1/entities/connections/matrix` | Full type-level edge matrix |
| `GET /api/v1/exchanges/{exchange_id}/integrity` | Verify invocation_ref ↔ receipt ↔ settlement |

---

## Normalized `invocation_ref` (exchange_settled v0.1)

Every `exchange_settled` ledger row carries an `invocation_ref` block linking operational invocation to settlement:

```json
{
  "spec_version": "pocp.invocation_ref.v0.1",
  "invocation_id": "inv_abc123",
  "trace_id": "trace_uuid",
  "source_entity_id": "human_001",
  "target_entity_id": "llm_001",
  "capability_id": "cap_001",
  "capability": "llm_inference",
  "usage": { "metering_mode": "token", "total_tokens": 150 },
  "receipt_hash": "sha256:…",
  "verification_ref": "sha256:…",
  "settlement_ref": "ex_abc123",
  "status": "settled",
  "timestamp": "2026-05-31T12:00:00"
}
```

| Field | Notes |
|-------|--------|
| `trace_id` | Optional link to `InvocationTrace` (multi-step chains) |
| `settlement_ref` | Exchange id (`ex_*`) — primary settlement anchor |
| `receipt_hash` | Compute/capability receipt integrity hash |
| `invocation_chain_digest` | In exchange proof — hash of step chain or flat ref |

---

## Legacy single-invocation shape (deprecated)

The flat caller/callee JSON below remains valid for exchange metering but **does not** replace InvocationTrace for contribution proofs:

```json
{
  "invocation_id": "invoke_001",
  "caller_entity_id": "human_001",
  "callee_entity_id": "agent_001",
  "capability_id": "cap_001",
  "cost_unit": "AIC",
  "cost_amount": 5,
  "status": "completed"
}
```
