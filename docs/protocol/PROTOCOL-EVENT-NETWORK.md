# Protocol Event Network (Overlay) v0.1

**Principle:** No PoCP-owned physical network — **ProtocolEvents** propagate over HTTPS between logical nodes, like Bitcoin blocks over the Internet.

Related: [ENTITY-DIALOGUE-PROTOCOL.md](./ENTITY-DIALOGUE-PROTOCOL.md) · [BITCOIN-INSPIRED-POCP-NETWORK.md](../../BITCOIN-INSPIRED-POCP-NETWORK.md) · [CHAIN-AND-NODE-PLAN-v0.1.md](./CHAIN-AND-NODE-PLAN-v0.1.md)

---

## 1. Unified stack (five layers)

```text
┌─────────────────────────────────────────────────────────────┐
│  L4  Policy      Trust Bundle · Finalization · Rights        │
├─────────────────────────────────────────────────────────────┤
│  L3  Semantic    Entity · Connection · Contribution · Proof │
├─────────────────────────────────────────────────────────────┤
│  L2  Dialogue    pocp.entity_dialogue.v0.1 (envelope)       │
├─────────────────────────────────────────────────────────────┤
│  L1.5 Overlay   ProtocolEvent · Mempool · EventBatch · Merkle│  ← this doc
├─────────────────────────────────────────────────────────────┤
│  L1  Binding     HTTPS REST · A2A · MCP (edge only)          │
├─────────────────────────────────────────────────────────────┤
│  L0  Internet    Existing IP/DNS — node overlay              │
└─────────────────────────────────────────────────────────────┘
```

**Dialogue** = who talks to whom (Entity refs, `kind`).  
**Overlay** = what happened (hash-linked `ProtocolEvent`, batched Merkle root, confirmation depth).

---

## 2. Dialogue kind → ProtocolEvent

| Dialogue `kind` | ProtocolEvent `event_type` | When |
|-----------------|----------------------------|------|
| `invoke` | `InvocationCreated` | Operational step recorded |
| `attest` | `VerificationCompleted` | Witness / verify advisory |
| `submit` | `ProofSubmitted` | Contribution opened |
| `federation_offer` | `FederatedProofOffered` | Cross-node proof package |
| `broadcast` | *(payload.event_type)* | Explicit overlay publish |
| `finalize_notice` | `SettlementExecuted` | Exchange / rights settled |

Bridge implementation: `backend/services/network/protocol_bridge.py`

---

## 3. Bitcoin mapping (operational)

| Bitcoin | PoCP overlay |
|---------|----------------|
| P2P gossip | HTTPS `POST .../overlay/gossip/receive` (trusted peers, v0.2b) |
| Mempool | `PoCPMempool` + `protocol_overlay_events` table (v0.2) |
| Block | `EventBatch` |
| Merkle root | `event_merkle_root` (display) + `merkle_root_hex` (ledger-compatible) |
| SPV | Light node verifies inclusion via `ledger_merkle` + batch proof |
| Confirmation depth | `ConfirmationService.status_for_event(level=…)` |

**Not copied:** PoW, public token issuance, energy race.

---

## 4. API (v0.1 pilot)

| Endpoint | Purpose |
|----------|---------|
| `GET /api/v1/intelligence/protocol/network` | Overlay manifest + stack position |
| `GET /api/v1/intelligence/network/overlay/status` | Mempool size, last batch |
| `POST /api/v1/intelligence/network/overlay/events` | Enqueue ProtocolEvent |
| `POST /api/v1/intelligence/network/overlay/batch` | Drain mempool → EventBatch |
| `GET /api/v1/intelligence/network/overlay/events` | List persisted events (`mempool_status`, `event_type`) |
| `POST /api/v1/intelligence/network/overlay/gossip/receive` | Inbound batch from trusted peer |
| `POST /api/v1/intelligence/network/overlay/gossip/push` | Push last batch to trusted peers |
| `POST /api/v1/intelligence/network/overlay/demo` | Full invoke→proof→verify→settle demo |
| `POST /api/v1/intelligence/dialogue` | L2 envelope (may emit overlay event via bridge) |

Smoke: `python backend/scripts/bitcoin_inspired_network_smoke.py`

---

## 5. Merkle unification (PN-3)

| Layer | Module | Root format |
|-------|--------|-------------|
| Ledger | `ledger_merkle.py` | bare hex |
| Event batch | `network/merkle.py` → `merkle_canonical.py` | `merkle_root_hex` + `sha256:` display |
| Contribution proof | `protocol_event_overlay` block | same algorithm + SPV inclusions per step |

`GET /api/v1/intelligence/protocol/merkle` — algorithm descriptor.

Proof packets include `protocol_event_overlay` when invocation steps exist (with `dialogue_refs` on each trace).

---

## 6. Evolution

| Version | Scope |
|---------|--------|
| v0.1 | In-process mempool; dialogue bridge; demo API; unified Merkle |
| v0.2 | **`protocol_overlay_events` / `protocol_overlay_batches`** (`POCP_OVERLAY_PERSIST=true`) |
| v0.2b | **Peer gossip** — `gossip/receive` + `gossip/push` (`POCP_OVERLAY_GOSSIP`) |
| v0.3 | Light-node SPV against ledger + batch roots |
| v0.4 | Cross-node live `broadcast` routing |

Code: `backend/services/network/` · tests: `backend/tests/test_protocol_network.py`
