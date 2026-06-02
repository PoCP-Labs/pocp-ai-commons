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
| `quote` | operational | Exchange intent before invoke | exchange intent (future) |
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

### 4.3 `federation_offer` / `federation_accept` — cross-node

**No new wire.** Same HTTPS Internet; different `node_id` on `from` / `to`.

```text
Node A  ── federation_offer(proof) ──►  Node B
Node B  ── federation_accept(result) ──►  Node A (optional)
```

- `federation_offer`: inline `payload.proof`, or `payload.contribution_id` with `fetch_peer: true` (default) to pull from trusted peer; `auto_import` optional.
- `federation_accept`: validate + optional `auto_import` (default true); enqueues `FederatedProofOffered` on overlay.
- Import side runs **Trust Policy Bundle** validation before mirror.
- HTTP relay without full envelope: `POST /api/v1/federation/overlay/relay`.
- Live cross-node `invoke`: set `to.node_id` to peer + `POCP_TRUSTED_NODES`; A forwards to `POST {peer}/api/v1/federation/dialogue`. See [CROSS-NODE-INTERNET.md](./CROSS-NODE-INTERNET.md).

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

| Kind | structural | protocol | operational |
|------|------------|----------|---------------|
| discover | read owner/created | — | read allowed targets |
| invoke | — | — | write InvocationStep |
| attest | — | write witness role | may ref trace |
| submit | — | write ContributionParticipant | may ref trace |
| federation_offer | — | proof import | receipt in proof |
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

---

## 9. Evolution path

| Phase | Scope |
|-------|-------|
| **v0.1 (pilot)** | Full kind set: `ping`, `discover`, `quote`, `invoke`, `attest`, `submit`, `finalize_notice`, `federation_*`, `broadcast` |
| v0.2 | `quote` + exchange spine integration; signed cross-node envelopes |
| v0.3 | REST/A2A convergence — all entity calls through dialogue router |
| v0.4 | Peer dialogue proxy with Ed25519; live cross-node invoke |

---

## 10. Code references

- Dialogue service: `backend/services/entity_dialogue.py`
- Router: `backend/routers/intelligence.py` (`/dialogue`, `/protocol/entity-dialogue`)
- Connection validation: `backend/intelligence/entity_ontology.py`
- Trust on import: `backend/services/trust_policy_bundle.py`
