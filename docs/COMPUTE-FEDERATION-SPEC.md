# Compute Federation Spec — v0.4

Cross-node PoCP Token settlement when compute jobs execute on a **trusted federation peer** (`source: peer_node`).

Related: [FEDERATION-v0.1.md](./FEDERATION-v0.1.md) · [COMPUTE-BALANCE-SPEC.md](./COMPUTE-BALANCE-SPEC.md) · [ENTITY-MARKET-SPEC.md](./ENTITY-MARKET-SPEC.md)

---

## Problem

Local bilateral settlement (`settle_bilateral`) debits the consumer and credits the provider **on the same node**. When inference or witness runs on a remote peer, only the consumer node should debit locally; the provider node must credit its own ledger asynchronously.

---

## v0.4 flow

```text
Consumer Node (A)                         Provider Node (B)
─────────────────                         ─────────────────
Job scheduled → peer_node
Execute via /intelligence/compute/*
       │
settle_federation_cross_node()
  • debit consumer wallet
  • FederationSettlement (side=consumer, status=consumer_debited)
  • ledger: ai_credits_burned + federation_settlement_intent
       │
POST /api/v1/federation/settlement/intent ──► apply_settlement_intent()
                                                • credit provider wallet*
                                                • FederationSettlement (side=provider)
                                                • ledger: compute_provided +
                                                  federation_settlement_mirrored
```

\* If `provider_entity_id` is absent or has no wallet, credit accrues to `pocp-entity-federation-local` on the provider node (Pilot escrow).

---

## Idempotency

| Key | Scope |
|-----|--------|
| `settlement_key` = `receipt_hash` | Unique per `(settlement_key, side)` |

Duplicate consumer debits or provider credits are rejected with `already_settled`.

---

## API

| Method | Path | Role |
|--------|------|------|
| `POST` | `/api/v1/federation/settlement/intent` | Provider node accepts signed intent |
| `GET` | `/api/v1/federation/settlements` | List local settlement records |

Intent payload: `pocp.federation_settlement.v0.4` — includes full `ComputeReceipt`, token amounts, and optional Ed25519 signature over a canonical message.

---

## Integration

- `compute_executor.complete_llm_job` and witness execution call `settle_compute_receipt()`, which routes `peer_node` jobs to federation settlement.
- Peer discovery: `compute_nodes.yaml` → `peer_compute` + `trusted_nodes.yaml`.
- Mirror push is best-effort; Pilot operators may reconcile via `GET /settlements` on both nodes.

---

## Pilot limits

- No on-chain escrow or dispute arbitration in v0.4.
- Signature verification uses trusted-node public keys when configured; set `POCP_FEDERATION_SETTLEMENT_REQUIRE_SIGNATURE=true` to enforce.
- Cross-node Skill split settlement remains a separate v0.4 track.
