# Binding → Dialogue Map v0.1

REST, A2A, and overlay routes are **bindings**. Native semantics live in **`pocp.entity_dialogue.v0.1`** and **`ProtocolEvent`**.

See [ENTITY-DIALOGUE-PROTOCOL.md](./ENTITY-DIALOGUE-PROTOCOL.md) · [PROTOCOL-EVENT-NETWORK.md](./PROTOCOL-EVENT-NETWORK.md)

---

## Entity ↔ Entity (same node)

| Binding (today) | Dialogue `kind` | Overlay event |
|-----------------|-----------------|---------------|
| `POST /api/v1/intelligence/dialogue` | *any* | via bridge |
| `POST .../dialogue` + `payload.execute: true` | `invoke` | `InvocationCreated` + metered execute |
| `POST /api/v1/contributions` | `submit` | `ProofSubmitted` |
| `POST /api/v1/contributions/{id}/auto-verify` | `attest` | `VerificationCompleted` |
| `POST /api/v1/wallets/me/quote` | `quote` | `ExchangeQuoted` (overlay) |
| `POST /api/v1/capabilities/skills/{id}/execute` | `invoke` | `InvocationCreated` |
| `POST /api/v1/capabilities/agents/{id}/execute` | `invoke` | `InvocationCreated` |
| `POST /api/v1/invocations` | `invoke` | `InvocationCreated` |
| `POST /api/v1/ai/chat` | `invoke` | `InvocationCreated` + `exchange_settled` (`exchange_kind: capability`, `legacy_event_type: ai_chat`) |
| `POST /api/v1/capabilities/mcp/{tool_entity_id}/invoke` | `invoke` | `InvocationCreated` + `exchange_settled` (`exchange_kind: capability`, `settlement_policy: mcp_invoke.v1`) |
| `POST /api/v1/intelligence/dialogue` + `payload.execute: true` | `invoke` | `InvocationCreated` + `exchange_settled` (via `capability.dialogue_invoke`) |
| `POST /api/v1/intelligence/entities/{id}/dialogue` + `payload.execute: true` | `invoke` | same as dialogue execute |
| `GET /api/v1/intelligence/entities/{id}/agent-card` | `discover` | — |
| A2A `SendMessage` | `submit` (deferred) | `ProofSubmitted` |

### Public node `/pocp/*` (Phase A shim)

| Binding | Dialogue `kind` | Exchange / overlay |
|---------|-----------------|-------------------|
| `POST /pocp/invoke` | any (`pocp.entity_dialogue.v0.1` envelope) | per `kind`; metered paths use exchange spine when `payload.execute=true` |
| `GET /pocp/capabilities` | `discover` (directory) | — |
| `POST /pocp/handshake` | — (federation discover + handshake) | — |
| `POST /pocp/proofs` | `attest` / proof verify | `VerificationCompleted` (when applicable) |
| `POST /pocp/settlements/ack` | `finalize_notice` | `SettlementExecuted` |
| `GET /pocp/sync` | `federation_offer` (bulk) | peer manifest |

Operator manifest lists these URLs under `endpoints.pocp_*` — see `GET /api/v1/intelligence/protocol/federation`.

---

## Metered execute bindings (operator manifest)

These bindings share **`kind: invoke`** and emit **`exchange_settled`** via the exchange spine. Operators discover stable URLs from `endpoints` on the federation manifest.

| Manifest key | Binding | Execute trigger | Overlay / settlement |
|--------------|---------|-----------------|----------------------|
| `ai_chat` | `POST /api/v1/ai/chat` | request body (LLM target) | `InvocationCreated` + `exchange_settled` (`exchange_kind: capability`, `legacy_event_type: ai_chat`) |
| `mcp_invoke` | `POST /api/v1/capabilities/mcp/{tool_entity_id}/invoke` | tool entity id in path | `InvocationCreated` + `exchange_settled` (`exchange_kind: capability`, `settlement_policy: mcp_invoke.v1`) |
| `intelligence_dialogue` | `POST /api/v1/intelligence/dialogue` | `payload.execute: true` | `InvocationCreated` + `exchange_settled` (via `capability.dialogue_invoke`) |
| `entity_dialogue` | `POST /api/v1/intelligence/entities/{entity_id}/dialogue` | `payload.execute: true` | same as `intelligence_dialogue` |

Pre-flight quote for metered paths: `endpoints.wallet_quote` → `POST /api/v1/wallets/me/quote` with `kind: quote`.

Cross-node L1 exchange proof import (no BC mint): `exchange_import.import_exchange_proof` on the federation manifest.

---

## Entity ↔ Entity (cross-node)

| Binding | Dialogue `kind` | Overlay |
|---------|-----------------|---------|
| `GET /api/v1/contributions/{id}/proof` | `federation_offer` (deref) | `FederatedProofOffered` |
| `POST /api/v1/federation/overlay/relay` | — (direct relay) | `FederatedProofOffered` |
| `POST /api/v1/federation/dialogue` | any dialogue `kind` | per kind |
| `POST /api/v1/federation/validate-proof` | `federation_offer` | validation only |
| `POST /api/v1/federation/import-proof` | `federation_accept` | import mirror |
| `POST /api/v1/federation/import-exchange-proof` | `federation_accept` | L1 exchange proof import (no BC mint) |
| `POST /api/v1/federation/sync` | `federation_offer` (bulk) | — |
| `POST /api/v1/contributions/{id}/finalize` | `finalize_notice` (`apply_finalize`) | `SettlementExecuted` |
| `GET /api/v1/contributions/{id}/verdict` | `finalize_notice` (inspect) | — |
| `POST /api/v1/contributions` | `submit` | `ProofSubmitted` |
| `POST /api/v1/contributions/{id}/auto-verify` | `attest` (`run_verify`) | `VerificationCompleted` |

---

## Entity ↔ outside world

| Binding | Boundary Entity | Receipt required |
|---------|-----------------|------------------|
| MCP tool invoke | `tool` | `CapabilityReceipt` |
| OpenAI / Ollama | `llm` | `CapabilityReceipt` |
| OAuth / browser | `human` | session only |
| GitHub API | `tool` / `human` | optional contribution |

External wire formats **must not** appear inside dialogue `payload` schema — only PoCP-normalized fields.

---

## Overlay-only bindings

| Binding | Action |
|---------|--------|
| `POST /api/v1/intelligence/network/overlay/events` | `broadcast` |
| `POST /api/v1/intelligence/network/overlay/batch` | seal mempool → batch |
| `POST /api/v1/intelligence/network/overlay/demo` | smoke path |

---

## Rule for new features

1. Declare **dialogue `kind`** (and optional **ProtocolEvent** type).
2. Implement handler in `entity_dialogue.route_dialogue` and/or `protocol_bridge`.
3. Expose REST as thin binding — do not invent parallel semantics.
