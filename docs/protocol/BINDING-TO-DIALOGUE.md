# Binding → Dialogue Map v0.1

REST, A2A, and overlay routes are **bindings**. Native semantics live in **`pocp.entity_dialogue.v0.1`** and **`ProtocolEvent`**.

See [ENTITY-DIALOGUE-PROTOCOL.md](./ENTITY-DIALOGUE-PROTOCOL.md) · [PROTOCOL-EVENT-NETWORK.md](./PROTOCOL-EVENT-NETWORK.md)

Operator manifest: `GET /api/v1/intelligence/protocol/federation` (includes `/pocp/*` + exchange import surfaces).

---

## Entity ↔ Entity (same node)

| Binding (today) | Dialogue `kind` | Overlay event | `exchange_kind` |
|-----------------|-----------------|---------------|-----------------|
| `POST /api/v1/intelligence/dialogue` | *any* | via bridge | — |
| `POST .../dialogue` + `payload.execute: true` | `invoke` | `InvocationCreated` | `capability` |
| `POST /api/v1/contributions` | `submit` | `ProofSubmitted` | — |
| `POST /api/v1/contributions/{id}/auto-verify` | `attest` | `VerificationCompleted` | `compute` |
| `POST /api/v1/wallets/me/quote` | `quote` | `ExchangeQuoted` (overlay) | `capability` |
| `POST /api/v1/capabilities/skills/{id}/execute` | `invoke` | `InvocationCreated` | `capability` \| `hybrid` |
| `POST /api/v1/capabilities/agents/{id}/execute` | `invoke` | `InvocationCreated` | `capability` \| `hybrid` |
| `POST /api/v1/invocations` | `invoke` | `InvocationCreated` | `capability` |
| `GET /api/v1/intelligence/entities/{id}/agent-card` | `discover` | — | — |
| A2A `SendMessage` | `submit` (deferred) | `ProofSubmitted` | — |

---

## Entity ↔ Entity (cross-node)

| Binding | Dialogue `kind` | Overlay | `exchange_kind` |
|---------|-----------------|---------|-----------------|
| `GET /api/v1/contributions/{id}/proof` | `federation_offer` (deref) | `FederatedProofOffered` | — |
| `POST /api/v1/federation/overlay/relay` | — (direct relay) | `FederatedProofOffered` | — |
| `POST /api/v1/federation/dialogue` | any dialogue `kind` | per kind | `capability` when `payload.execute=true` |
| `POST /api/v1/federation/validate-proof` | `federation_offer` | validation only | — |
| `POST /api/v1/federation/import-proof` | `federation_accept` | import mirror | — |
| `POST /api/v1/federation/import-exchange-proof` | `federation_accept` | exchange proof import | — |
| `POST /api/v1/federation/sync` | `federation_offer` (bulk) | — | — |
| `POST /api/v1/contributions/{id}/finalize` | `finalize_notice` (`apply_finalize`) | `SettlementExecuted` | — |
| `GET /api/v1/contributions/{id}/verdict` | `finalize_notice` (inspect) | — | — |
| `POST /api/v1/contributions` | `submit` | `ProofSubmitted` | — |
| `POST /api/v1/contributions/{id}/auto-verify` | `attest` (`run_verify`) | `VerificationCompleted` | `compute` |

---

## Public node (`/pocp/*` aliases)

Phase A shim — **no new semantics**; routes alias existing handlers ([PUBLIC-NODE-PROTOCOL.md](./PUBLIC-NODE-PROTOCOL.md)).

| Binding | Dialogue `kind` | Notes |
|---------|-----------------|-------|
| `GET /pocp/node` | — | instance manifest + endpoint map |
| `GET /pocp/health` | — | liveness |
| `GET /pocp/capabilities` | — | provider directory |
| `GET /pocp/protocol` | — | operator route map |
| `GET /pocp/sync` | — | peer manifest; `?run=true` pushes sync |
| `POST /pocp/handshake` | — | federation connect |
| `POST /pocp/invoke` | `invoke` \| `quote` \| `ping` | same as `POST /api/v1/federation/dialogue`; metered when `payload.execute=true` |
| `POST /pocp/proofs` | — | offline proof verify |
| `POST /pocp/settlements/ack` | — | federation settlement intent |

---

## Metered application bindings (exchange spine)

Bindings that **must** emit `exchange_settled` ([EXCHANGE-SPINE-v0.1.md](./EXCHANGE-SPINE-v0.1.md)).

| Binding | Dialogue `kind` | `exchange_kind` | Receipt / trace |
|---------|-----------------|-----------------|-----------------|
| `POST /api/v1/ai/chat` | `invoke` | `capability` (`legacy_event_type`: `ai_chat`) | `exchange_spine.settle_flat_metered_invoke` |
| `POST /api/v1/capabilities/mcp/{tool_entity_id}/invoke` | `invoke` | `capability` (`mcp_tool_call`) | `CapabilityReceipt` + `security_audit` |
| `POST /api/v1/intelligence/compute/mcp/invoke` | `invoke` | `capability` | remote MCP peer path |
| `POST /api/v1/intelligence/dialogue` + `payload.execute: true` | `invoke` | `capability` | `dialogue_invoke` → `capability_execute` |
| `POST /api/v1/intelligence/entities/{id}/dialogue` + `payload.execute: true` | `invoke` | `capability` | same as above |
| `POST /api/v1/federation/dialogue` + `payload.execute: true` | `invoke` | `capability` | cross-node when peer route enabled |
| `POST /pocp/invoke` + `payload.execute: true` | `invoke` | `capability` | public alias of federation dialogue |

**Quote before invoke:** `kind=quote` on dialogue or `POST /api/v1/wallets/me/quote`; follow with `invoke` using `refs.exchange_id` from quote result.

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
4. Register metered bindings in `GET /api/v1/intelligence/protocol/federation` → `metered_bindings`.
