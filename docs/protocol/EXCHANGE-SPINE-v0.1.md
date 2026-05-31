# Exchange Spine v0.1

**The chain is the pathway for compute and intelligence exchange** — not merely a contribution scoreboard.

Every BC movement tied to capability use **must** leave a recoverable exchange trail: intent → execution → settlement.

---

## 1. Exchange lifecycle

```text
exchange_intent     (optional, pre-flight quote)
       ↓
exchange_executed   (receipt + invocation trace sealed)
       ↓
exchange_settled    (ledger + credit_transactions)
       ↓
exchange_finalized  (contribution path only — CP mint)
```

| Stage | When | Ledger `event_type` (v0.4) | Legacy types (v0.3) |
|-------|------|---------------------------|---------------------|
| Intent | Quote accepted | `exchange_intent` | — |
| Executed | Receipt written | `exchange_executed` | — |
| Settled | BC moved | **`exchange_settled`** | `compute_provided`, `compute_consumed`, `ai_chat`, `capability_*` |
| Finalized | CP issued | `contribution_finalized` | `contribution_approved` |

**Migration rule:** New code emits `exchange_settled` with `metadata.legacy_event_type` for backward-compatible readers.

---

## 2. Canonical `exchange_settled` payload

```json
{
  "event_type": "exchange_settled",
  "entity_id": "entity_consumer",
  "payload": {
    "exchange_id": "ex_abc123",
    "exchange_kind": "compute | capability | hybrid",
    "consumer_entity_id": "human_001",
    "provider_entity_ids": ["skill_gpu_001", "llm_lumen_0"],
    "receipt_hash": "sha256:…",
    "invocation_trace_id": "trace_…",
    "capability_id": "cap_gpu_inference",
    "usage": {
      "input_tokens": 1200,
      "output_tokens": 400,
      "gpu_seconds": 12.5,
      "bc_debited": 15,
      "bc_credited": 12
    },
    "credit_transaction_ids": ["tx_debit_…", "tx_credit_…"],
    "settlement_policy": "compute_settlement.v1",
    "legacy_event_type": "compute_provided"
  }
}
```

---

## 3. Exchange kinds

| Kind | Examples | Provider roles | Consumer pays |
|------|----------|----------------|---------------|
| `compute` | GPU inference, training attestation | Compute Node, PC provider | BC (compute pool) |
| `capability` | LLM chat, Skill invoke, Agent run, MCP tool | LLM, Skill, Agent, Tool Entity | BC (AI credits) |
| `hybrid` | Agent + Skill + LLM chain | Multiple | Split per step |

> **Naming:** Product copy uses **算力 + 能力**. Payload field is `capability` (v0.4). Legacy payloads may use `intelligence` — readers should treat as alias.

---

## 4. Binding rules (Constitution Art. II)

1. **`credit_transactions.ledger_record_id`** — required for production settlement (Phase 1 migration).
2. **`receipt_hash`** — must match `CapabilityReceipt` or `ComputeReceipt` in proof packet.
3. **`invocation_trace_id`** — required when settlement follows multi-hop invocation.
4. **Atomicity** — debit, credit(s), and ledger row in **one DB transaction** (`finalize_exchange_settlement()`).

---

## 5. Proof packet extension

Add to portable proof:

```json
{
  "exchange_inclusion": {
    "exchange_id": "ex_abc123",
    "ledger_record_id": "lr_…",
    "ledger_merkle_proof": ["…"],
    "receipt_hash": "sha256:…"
  }
}
```

Verifiers replay: receipt → trace → ledger row → merkle proof → anchor.

---

## 6. Code mapping (current → target)

| Flow | Current service | Target function |
|------|-----------------|-----------------|
| GPU settlement | `compute_settlement.py` | `emit_exchange_settled(...)` |
| AI chat burn | `ai_chat.py` | same |
| Capability invoke | `capability_execute.py` | same |
| Federation compute | `federation_settlement.py` | same |
| Wallet UI category | `wallet_ledger_link.py` | read `exchange_kind` from payload |

**New module (planned):** `backend/services/exchange_spine.py`

```python
def emit_exchange_settled(
    db,
    *,
    consumer_entity_id: str,
    provider_entity_ids: list[str],
    exchange_kind: str,
    receipt_hash: str,
    usage: dict,
    credit_tx_rows: list[CreditTransaction],
    invocation_trace_id: str | None = None,
    legacy_event_type: str | None = None,
) -> LedgerRecord: ...
```

---

## 7. Anchor extension (Phase 2)

Optional fourth root in anchor metadata:

```json
{
  "ledger_merkle_root": "…",
  "graph_merkle_root": "…",
  "exchange_merkle_root": "…"
}
```

`exchange_merkle_root` = Merkle over all `exchange_settled` rows since last anchor (or subset hash embedded in ledger).

---

## 8. API surface (planned)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/v1/exchanges/{exchange_id}` | Full exchange record |
| GET | `/api/v1/entities/{id}/exchanges` | Entity's exchange history |
| POST | `/api/v1/exchanges/verify` | Offline verify receipt ↔ ledger |

Read-only in Phase 1; write paths remain internal via settlement services.
