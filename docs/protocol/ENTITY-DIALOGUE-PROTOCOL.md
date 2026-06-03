# Entity Dialogue Protocol v0.1

**Principle:** *Every Entity conversation uses one native envelope; bindings are adapters, not semantics.*  
**中文：** *Entity 之间与外界之间，语义走 PoCP 信封，传输走 Internet 绑定。*

This document defines **how Entities talk** — the missing **L2 Dialogue layer** between semantic primitives (Entity, Contribution, Proof) and transport bindings (HTTPS, MCP, vendor LLM APIs).

Related: [ENTITY-CONNECTION.md](./ENTITY-CONNECTION.md) · [PROTOCOL-EVENT-NETWORK.md](./PROTOCOL-EVENT-NETWORK.md) · [BINDING-TO-DIALOGUE.md](./BINDING-TO-DIALOGUE.md) · [CHAIN-AND-NODE-PLAN-v0.1.md](./CHAIN-AND-NODE-PLAN-v0.1.md) · [TRUST-POLICY-BUNDLE.md](./TRUST-POLICY-BUNDLE.md)

---

## 1. Why this layer exists

PoCP already defines **what** is said (schemas, connection matrix, proof packets). Today **how** it is said is fragmented:

| Surface today | Role | Problem |
|---------------|------|---------|
| REST `/api/v1/*` | Same-node CRUD | Many routes, no unified semantics |
| A2A JSON-RPC | Agent discovery / tasks | External protocol bolted on |
| MCP / vendor LLM | Tool / model adapters | Correct at boundary, must not leak inward |
| Federation import | Cross-node proof sync | Async mailbox, not live dialogue |

**Entity Dialogue Protocol (EDP)** is the native wire **semantics** — not a new physical network. Nodes deploy on ordinary HTTPS endpoints; EDP is the overlay message grammar.

---

## 2. Protocol stack (five layers)

```text
┌─────────────────────────────────────────────────────────────┐
│  L4  Policy      Trust Policy Bundle · Finalization · Rights │
├─────────────────────────────────────────────────────────────┤
│  L3  Semantic    Entity · Connection · Contribution · Proof  │
├─────────────────────────────────────────────────────────────┤
│  L2  Dialogue    pocp.entity_dialogue.v0.1  ← this document  │
├─────────────────────────────────────────────────────────────┤
│  L1.5 Overlay    ProtocolEvent · Mempool · EventBatch         │
├─────────────────────────────────────────────────────────────┤
│  L1  Binding     HTTPS · JSON · (A2A/MCP only at boundary)  │
├─────────────────────────────────────────────────────────────┤
│  L0  Internet    No PoCP-owned physical network — node overlay │
└─────────────────────────────────────────────────────────────┘
```

Overlay detail: [PROTOCOL-EVENT-NETWORK.md](./PROTOCOL-EVENT-NETWORK.md)

---

## 3. Dialogue envelope

Schema: **`pocp.entity_dialogue.v0.1`**

```json
{
  "schema": "pocp.entity_dialogue.v0.1",
  "dialogue_id": "dlg_01HXYZ…",
  "kind": "invoke",
  "from": {
    "entity_id": "ent_human_alice",
    "portable_id": "github:alice",
    "node_id": "pocp-node-a"
  },
  "to": {
    "entity_id": "ent_skill_tutor",
    "portable_id": "pocp:skill/r-tutor",
    "node_id": "pocp-node-a"
  },
  "payload": {
    "action": "uses",
    "input": { "topic": "PoCP protocol" }
  },
  "refs": {
    "invocation_trace_id": null,
    "contribution_id": null,
    "task_id": null,
    "proof_hash": null
  },
  "crypto": {
    "suite": null,
    "signature": null
  }
}
```

| Field | Required | Meaning |
|-------|----------|---------|
| `schema` | yes | Must be `pocp.entity_dialogue.v0.1` |
| `dialogue_id` | yes | Correlation id for request/response pair |
| `kind` | yes | Dialogue intent (see §4) |
| `from` / `to` | yes | Entity endpoint refs (at least one id or portable_id each) |
| `payload` | kind-dependent | Kind-specific body |
| `refs` | no | Links to memory artifacts (trace, contribution, proof) |
| `crypto` | cross-node | Signature when routing across trusted nodes (future) |

**Entity ref** — at least one of `entity_id` or `portable_id`; `node_id` required when target may be remote.

**Response envelope:** `pocp.entity_dialogue_response.v0.1` — same `dialogue_id`, adds `status` (`accepted` | `rejected` | `deferred`) and `result`.

---

## 4. Dialogue kinds

| Kind | Connection layer | Purpose | Memory artifact |
|------|------------------|---------|-----------------|
| `ping` | — | Node / entity liveness | none |
| `discover` | structural | Resolve entity profile + bindings | none |
| `quote` | operational | Pre-invoke exchange intent (wallet + `exchange_id`) | `exchange_id` in refs; `ExchangeQuoted` overlay (v0.2 ledger) |
| `invoke` | operational | Runtime call along edge matrix | InvocationTrace + CapabilityReceipt |
| `attest` | protocol | Witness / verify advisory | AiVerification |
| `submit` | protocol | Open contribution event | ContributionEvent |
| `finalize_notice` | protocol | Policy finalization notice | ledger / status |
| `federation_offer` | protocol | Offer signed proof for import | Contribution Proof Packet |
| `federation_accept` | protocol | Accept / validate offered proof | FederatedImport |

### 4.1 `invoke` — Entity ↔ Entity (operational)

Maps to [ENTITY-CONNECTION](./ENTITY-CONNECTION.md) invocation edge matrix. Payload:

```json
{
  "action": "uses | calls | invokes_llm | invokes_mcp | …",
  "input": { },
  "capability_type": "skill_invocation",
  "unit": "skill_invocation"
}
```

Rules:

1. `(from_type, to_type, action)` must pass `validate_invocation_edge`.
2. Every completed invoke **must** produce or extend an `InvocationTrace` with `pocp.capability_receipt.v0.1` when metered.
3. Routine invoke stays on **Exchange Chain**; promotion to Contribution is explicit (`submit` kind or flag).

**Binding shortcuts (v0.1):** REST `/api/v1/capabilities/*`, A2A `SendMessage` — must converge through dialogue handler over time.

### 4.2 `attest` / `submit` — Entity ↔ Entity (protocol)

- **`attest`**: advisory witness on an existing contribution or invocation ref. Maps to auto-verify pipeline.
- **`submit`**: creates Contribution Event + participants. Maps to `POST /api/v1/contributions`.

Participant roles must fit entity types per ontology.

### 4.3 `federation_offer` / `federation_accept` — cross-node (protocol layer)

**No new wire.** Same HTTPS Internet; different `node_id` on `from` / `to`. Both kinds sit on the [ENTITY-CONNECTION](./ENTITY-CONNECTION.md) **protocol** layer (proof import, not operational invoke).

```text
Node A  ── federation_offer(proof) ──►  Node B
Node B  ── federation_accept(result) ──►  Node A (optional ack)
```

| Kind | Default `auto_import` | Trust bundle | Overlay event |
|------|----------------------|--------------|---------------|
| `federation_offer` | `false` | `validate_proof_against_trust_policy` (dry-run or relay) | `FederatedProofOffered` |
| `federation_accept` | `true` | same validator; blocks when `blocking_valid` is false | `FederatedProofOffered` |

Shared payload fields:

| Field | Required | Meaning |
|-------|----------|---------|
| `payload.proof` | one of proof or contribution_id | Inline `pocp_contribution_proof` packet |
| `payload.contribution_id` | one of proof or contribution_id | Deref from `payload.source_node_id` when `fetch_peer: true` |
| `payload.source_node_id` | cross-node | Trusted peer id (falls back to `from.node_id`) |
| `payload.fetch_peer` | no | Default `true` for offer; accept fetches when proof omitted |
| `payload.auto_import` | no | Run `import_from_proof_packet` after validation |

**Trust Policy Bundle** ([TRUST-POLICY-BUNDLE.md](./TRUST-POLICY-BUNDLE.md)): both kinds call `validate_proof_against_trust_policy` before overlay enqueue. Failed checks surface in `result.validation.checks[]`; `status` is `rejected` when `blocking_valid` is false. Import rules (`validate_invocation_edges`, `min_witness_count`, …) apply identically to `POST /api/v1/federation/import-proof`.

Bindings (no envelope): `POST /api/v1/federation/overlay/relay`, `POST /api/v1/federation/validate-proof`, `POST /api/v1/federation/import-proof` — see [BINDING-TO-DIALOGUE.md](./BINDING-TO-DIALOGUE.md).

Live cross-node dialogue: `POST {peer}/api/v1/federation/dialogue` with trust list (`POCP_TRUSTED_NODES`). Operational `invoke` peer route: [CROSS-NODE-INTERNET.md](./CROSS-NODE-INTERNET.md).

This is **overlay routing** on existing URLs — not a PoCP-owned IP network.

### 4.4 External boundary — Entity ↔ outside world

Outside protocols **never** enter the semantic kernel. They terminate at adapter Entities:

```text
  MCP / OpenAI / GitHub / Browser
           │
           ▼  (external binding)
  Tool Entity · LLM Entity · Human Entity
           │
           ▼  pocp.entity_dialogue (invoke)
  Agent · Skill · Workflow · …
```

Rules:

1. External call crosses boundary only through a registered Entity (`tool`, `llm`, `human`).
2. Return path **must** write CapabilityReceipt + exchange spine when metered.
3. MCP/OpenAI wire format stays in `metadata.service_endpoints` — not in dialogue payload schema.

### 4.5 `quote` — operational pre-flight (v0.2 draft)

Maps to [ENTITY-CONNECTION](./ENTITY-CONNECTION.md) **operational** layer: validates `(from_type, to_type, action)` via `validate_invocation_edge` before any metered `invoke`. Aligns with [EXCHANGE-SPINE-v0.1.md](./EXCHANGE-SPINE-v0.1.md) stage **exchange_intent**.

**Rules (v0.1 pilot handler):**

1. `from` entity **must** be `human` (billing anchor) — same constraint as metered `invoke`.
2. `payload.action` optional; inferred from invocation edge matrix when omitted.
3. `payload.quote_action`: `capability_invoke` (default for skill/agent targets) or `ai_chat` (LLM targets).
4. Response assigns `refs.exchange_id`; consumer should pass it on subsequent `invoke` (`refs.exchange_id` or `payload.exchange_id`) so step metadata links the chain.
5. Overlay emits `ExchangeQuoted` when bridge is enabled; ledger `exchange_intent` row is **v0.2** (not yet required for pilot acceptance).

Request payload (capability invoke):

```json
{
  "action": "uses",
  "quote_action": "capability_invoke",
  "estimated_cost": 5.0,
  "exchange_id": null
}
```

Response `result` (summary):

```json
{
  "mode": "exchange_quote",
  "exchange_id": "ex_a1b2c3…",
  "exchange_kind": "hybrid",
  "quote": {
    "action": "capability_invoke",
    "credit_type": "ai_credits",
    "cost": 5.0,
    "current_balance": 50.0,
    "balance_after": 45.0,
    "allowed": true,
    "target_entity_id": "ent_skill_…",
    "target_entity_type": "skill"
  }
}
```

Binding equivalent: `POST /api/v1/wallets/me/quote` — dialogue `quote` is the native kind; wallet route remains a thin binding.

### 4.6 `federation_accept` — accept offered proof (v0.2 draft)

Semantically **import-side** confirmation of a proof already offered or relayed. Differs from `federation_offer` only in default `auto_import: true` and typical consumer role (importer node).

Request:

```json
{
  "schema": "pocp.entity_dialogue.v0.1",
  "dialogue_id": "dlg_fed_acc_1",
  "kind": "federation_accept",
  "from": { "entity_id": "ent_human_importer", "node_id": "pocp-node-b" },
  "to": { "node_id": "pocp-node-a" },
  "payload": {
    "source_node_id": "pocp-node-a",
    "proof": { "proof_type": "pocp_contribution_proof", "…": "…" },
    "auto_import": true
  }
}
```

Response `result` includes `validation` (trust bundle), `overlay_event`, and optional `import` (`federated_import_id` when `auto_import` succeeds). `status` is `accepted` only when `blocking_valid` and import (if requested) succeed.

---

## 5. Routing model (logical nodes, physical Internet)

```text
                    Internet (HTTPS)
                          │
         ┌────────────────┴────────────────┐
         │                                 │
    Node A (node-a)                   Node B (node-b)
    BACKEND_URL                       BACKEND_URL
         │                                 │
    POST /api/v1/intelligence/dialogue     │
    POST …/entities/{id}/dialogue          │
         │                                 │
    dialogue_router ──local──► handlers    │
         │                                 │
         └── cross-node (future) ─────────► peer dialogue endpoint
                                           validate-proof / import-proof
```

| Scope | Endpoint | Auth |
|-------|----------|------|
| Node-wide | `POST /api/v1/intelligence/dialogue` | Session / API key |
| Entity-targeted | `POST /api/v1/intelligence/entities/{entity_id}/dialogue` | Session; `to.entity_id` must match |
| Manifest | `GET /api/v1/intelligence/protocol/entity-dialogue` | Public |
| Federation node card | `GET /api/v1/federation/node` includes dialogue URL | Public |

Peer cross-node invoke uses existing peer trust headers (`POCP_PEER_COMPUTE_SECRET`, Ed25519) — same trust plane as federated witness.

---

## 6. Mapping dialogue kinds → connection layers

Aligned with [ENTITY-CONNECTION.md](./ENTITY-CONNECTION.md) three layers and [TRUST-POLICY-BUNDLE.md](./TRUST-POLICY-BUNDLE.md) import rules.

| Kind | structural | protocol | operational |
|------|------------|----------|---------------|
| discover | read owner/created | — | read allowed targets |
| quote | — | — | edge matrix check + exchange intent |
| invoke | — | — | write InvocationStep / metered execute |
| attest | — | write witness role | may ref trace |
| submit | — | write ContributionParticipant | may ref trace |
| finalize_notice | — | finalization policy | — |
| federation_offer | — | proof validate + overlay | receipt in proof |
| federation_accept | — | proof validate + import | receipt in proof |
| broadcast | — | ProtocolEvent enqueue | — |
| ping | — | — | — |

---

## 7. Native vs binding (anti–拼装车)

| Native (kernel) | Binding (edge) |
|-----------------|----------------|
| `pocp.entity_dialogue.v0.1` envelope | FastAPI route paths |
| Connection matrix validation | A2A JSON-RPC framing |
| InvocationTrace + receipt | MCP JSON-RPC to tool server |
| Proof packet + trust bundle | OpenAI Chat Completions API |
| Ledger / exchange_settled | OAuth browser redirect |

**Rule:** New integrations must declare which **dialogue kind** they implement. A new REST route without a dialogue kind mapping is technical debt.

---

## 8. API surface (v0.1 pilot)

| Endpoint | Purpose |
|----------|---------|
| `GET /api/v1/intelligence/protocol/entity-dialogue` | Schema, kinds, stack position |
| `POST /api/v1/intelligence/dialogue` | Route any envelope on this node |
| `POST /api/v1/intelligence/entities/{entity_id}/dialogue` | Route to specific entity |

### Example: discover

Request:

```json
{
  "schema": "pocp.entity_dialogue.v0.1",
  "dialogue_id": "dlg_discover_1",
  "kind": "discover",
  "from": { "entity_id": "human-1", "node_id": "pocp-node-a" },
  "to": { "entity_id": "skill-1", "node_id": "pocp-node-a" },
  "payload": {}
}
```

Response `result` includes entity profile, connection spec, and **binding hints** (REST URLs for backward compatibility).

### Example: invoke (operational step)

**Trace only** (default): records one `InvocationStep` on `InvocationTrace`.

**Metered execute** (`payload.execute: true`): runs `execute_skill` / `execute_agent`, writes full chain + billing + overlay event.

```json
{
  "kind": "invoke",
  "payload": {
    "execute": true,
    "input": "Explain the five-layer protocol stack",
    "llm_provider": "mock"
  }
}
```

Returns `refs.invocation_trace_id`, `result.executed`, and optional `overlay.protocol_event`.

### Example: quote (operational pre-flight)

```json
{
  "schema": "pocp.entity_dialogue.v0.1",
  "dialogue_id": "dlg_quote_1",
  "kind": "quote",
  "from": { "entity_id": "human-1", "node_id": "pocp-node-a" },
  "to": { "entity_id": "skill-1", "node_id": "pocp-node-a" },
  "payload": { "quote_action": "capability_invoke" }
}
```

Response binds `refs.exchange_id`; follow with `invoke` and the same `exchange_id` in `refs` before `payload.execute: true`.

### Example: federation_accept (cross-node import)

```json
{
  "schema": "pocp.entity_dialogue.v0.1",
  "dialogue_id": "dlg_fed_1",
  "kind": "federation_accept",
  "from": { "entity_id": "human-1", "node_id": "pocp-node-b" },
  "to": { "node_id": "pocp-node-a" },
  "payload": {
    "source_node_id": "pocp-node-a",
    "contribution_id": "contrib_peer_1",
    "auto_import": true
  }
}
```

Importer must list `pocp-node-a` in `POCP_TRUSTED_NODES`. Validation uses this node's published trust policy bundle.

---

## 9. Evolution path

| Phase | Scope |
|-------|-------|
| **v0.1 (pilot)** | Envelope + handlers: `ping`, `discover`, `invoke`, `attest`, `submit`, `finalize_notice`, `federation_*`, `broadcast`; **quote** + **federation_accept** handlers ship in pilot (see §4.5–4.6) |
| **v0.2** | Formalize §4.5–4.6: ledger `exchange_intent` on `quote`; trust-bundle check ids in federation responses; signed cross-node `crypto` |
| v0.3 | REST/A2A convergence — all entity calls through dialogue router |
| v0.4 | Peer dialogue proxy with Ed25519; live cross-node invoke |

### v0.1 audit notes (PL-1)

| Gap (pre-audit) | Resolution |
|-----------------|------------|
| `quote` marked "future" in kind table | §4.5 documents pilot handler + exchange spine intent stage |
| No trust-bundle linkage on `federation_accept` | §4.3 + §4.6 reference `validate_proof_against_trust_policy` |
| §6 missing `quote`, `finalize_notice`, `federation_accept` | Table expanded; cross-links ENTITY-CONNECTION + TRUST-POLICY-BUNDLE |
| No payload examples for quote / federation_accept | §8 examples added |
| ENTITY-CONNECTION silent on dialogue kinds | See ENTITY-CONNECTION §8 |

---

## 10. Code references

- Dialogue service: `backend/services/entity_dialogue.py`
- Router: `backend/routers/intelligence.py` (`/dialogue`, `/protocol/entity-dialogue`)
- Connection validation: `backend/intelligence/entity_ontology.py`
- Trust on import: `backend/services/trust_policy_bundle.py`
