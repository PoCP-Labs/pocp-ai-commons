# PoCP Network Architecture — 12 Layers

PoCP Neural Commons Network stacks twelve protocol layers. This repo (`pocp-ai-commons`) implements **Phase A reference slices** of each layer; gaps are explicit so Agent Studio and contributors know what is real vs planned.

Parent doc: [CAPABILITY-INTERNET-PROTOCOL.md](./CAPABILITY-INTERNET-PROTOCOL.md)

---

## Layer map

```text
PoCP Capability Internet
│
├──  1. Entity Layer              智能主体层
├──  2. Node Layer                节点层
├──  3. Identity Layer            去中心化身份层
├──  4. Capability Layer          能力注册层
├──  5. Discovery Layer           节点发现层
├──  6. Invocation Layer          调用账本层
├──  7. Proof Layer               贡献证明层
├──  8. Verification Layer        验证层
├──  9. Settlement Layer          结算层
├── 10. Reputation Graph Layer    声誉图谱层
├── 11. Governance Layer          治理层
└── 12. Protocol Economy Layer    协议经济层
```

---

## Implementation status (pocp-ai-commons)

| # | Layer | Spec / doc | Code (backend) | Phase A status |
|---|--------|------------|----------------|----------------|
| 1 | **Entity** | [ENTITY-LAYER-SPEC.md](./protocol/ENTITY-LAYER-SPEC.md), [01-ENTITY-REGISTRY.md](./architecture/01-ENTITY-REGISTRY.md) | `models/entity.py`, `services/entity_catalog.py`, `intelligence/entity_ontology.py` | **14 types seeded**; catalog audit + stable infrastructure IDs |
| 2 | **Node** | [NODE-RUNTIME-SPEC.md](./protocol/NODE-RUNTIME-SPEC.md), [PUBLIC-NODE-PROTOCOL.md](./protocol/PUBLIC-NODE-PROTOCOL.md) | `models/node_profile.py`, `services/node/`, `services/node_manifest.py`, `services/cip/node/` | **`node_profiles` table**; well-known manifest; catalog → NodeProfile bootstrap |
| 3 | **Identity** | [DID-SIGNATURE-SPEC.md](./protocol/DID-SIGNATURE-SPEC.md), [TRUST-POLICY-BUNDLE.md](./protocol/TRUST-POLICY-BUNDLE.md) | `services/federation_*.py`, ledger signatures | Federation import signatures; **DID/VC not yet** |
| 4 | **Capability** | [CAPABILITY-SCHEMA.md](./protocol/CAPABILITY-SCHEMA.md), [02-CAPABILITY-REGISTRY.md](./architecture/02-CAPABILITY-REGISTRY.md) | `services/cip/capability/`, `services/capability/` | CIP + production registry; **public node manifest partial** |
| 5 | **Discovery** | [CROSS-NODE-INTERNET.md](./protocol/CROSS-NODE-INTERNET.md), [03-NEURAL-ROUTING.md](./architecture/03-NEURAL-ROUTING.md) | `services/cip/discovery/`, `services/neural/rule_based_router.py` | CIP discovery service; **no DHT/libp2p** |
| 6 | **Invocation** | [INVOCATION-LEDGER-SPEC.md](./protocol/INVOCATION-LEDGER-SPEC.md), [04-INVOCATION-LEDGER.md](./architecture/04-INVOCATION-LEDGER.md) | `services/cip/invocation/`, `services/invocation_ledger.py` | CIP ledger + production traces |
| 7 | **Proof** | [PROOF-SPEC.md](./protocol/PROOF-SPEC.md), [05-VERIFICATION-PROOF.md](./architecture/05-VERIFICATION-PROOF.md) | `services/cip/proof/`, `services/proof.py` | CIP proof service + portable export |
| 8 | **Verification** | [VERIFICATION-NETWORK-SPEC.md](./protocol/VERIFICATION-NETWORK-SPEC.md) | `services/cip/verification/`, `services/verifiers/` | CIP verifier + multi-witness advisory |
| 9 | **Settlement** | [SETTLEMENT-SPEC.md](./protocol/SETTLEMENT-SPEC.md), [07-SETTLEMENT-LAYER.md](./architecture/07-SETTLEMENT-LAYER.md) | `services/cip/settlement/`, `services/exchange_spine.py` | CIP settlement + exchange spine |
| 10 | **Reputation** | [REPUTATION-GRAPH-SPEC.md](./protocol/REPUTATION-GRAPH-SPEC.md), [08-REPUTATION-GOVERNANCE.md](./architecture/08-REPUTATION-GOVERNANCE.md) | `services/cip/reputation/`, `services/graph.py` | CIP reputation graph; **event-sourced indexer backlog** |
| 11 | **Governance** | [GOVERNANCE-SPEC.md](./protocol/GOVERNANCE-SPEC.md), [08-REPUTATION-GOVERNANCE.md](./architecture/08-REPUTATION-GOVERNANCE.md) | org foundation, reviewer queue, policy bot | Demo governance proxy; **PIP process draft** |
| 12 | **Economy** | [PROTOCOL-ECONOMY-SPEC.md](./protocol/PROTOCOL-ECONOMY-SPEC.md), [06-TOKEN-MEASUREMENT.md](./architecture/06-TOKEN-MEASUREMENT.md) | `services/cip/economy/`, wallets, `services/token_measurement/` | CIP accounting + internal metering — **no public token** |

Legend: **bold** = materially present in tree; plain = partial; “not yet” = spec-only.

---

## Layers 1–2 (Entity + Node) — CI-1 / CI-2

```text
Entity (L1)                          Node (L2)
──────────                           ─────────
entities table                     node_profiles table
14 ontology types                  NodeProfile per active provider Entity
entity_catalog.py bootstrap   →    _ensure_node_profiles() on repair
stable infrastructure IDs          well-known + per-entity manifests
intelligence/entity_ontology.py    services/node/schemas.py (frozen contract)
services/entity/schemas.py (CI-1 IDs)   services/entity/base.py (catalog Protocol)
                                        services/node/base.py (node + well-known Protocol)
```

| Handoff | Deliverable | Code / doc |
|---------|-------------|------------|
| CI-1 | Entity catalog complete | `services/entity_catalog.py`, `services/entity/schemas.py`, [ENTITY-LAYER-SPEC.md](./protocol/ENTITY-LAYER-SPEC.md) |
| CI-2 | NodeProfile + well-known draft | `services/node/schemas.py`, `services/node/base.py`, [NODE-RUNTIME-SPEC.md](./protocol/NODE-RUNTIME-SPEC.md), [PUBLIC-NODE-PROTOCOL.md](./protocol/PUBLIC-NODE-PROTOCOL.md) |
| Wire | Instance discovery | `GET /.well-known/pocp-node.json` in `backend/main.py` |
| Wire | Entity facets | `GET /api/v1/entities/{id}/node-manifest` |

Tests: `pytest backend/tests/test_entity_ontology.py backend/tests/test_entity_catalog.py -q` (from `backend/`).

---

## Data objects (target v1)

| Object | Table / service today | Gap |
|--------|----------------------|-----|
| Entity | `entities` | — |
| NodeProfile | `node_profiles` (+ `entity_catalog` bootstrap) | signed heartbeat events (Phase B) |
| Capability | `entity_capabilities` | Phase B `/pocp/capabilities` wire parity |
| Invocation | `invocation_traces`, `invocation_steps` | full state machine on public nodes |
| Proof | contribution evidence + proof export | signed proof events |
| Verification | `contribution_verifications`, disputes | standalone verifier node API |
| Settlement | `exchange_settled`, policies | signed settlement events |
| TokenAccount | wallet services | cross-node replay |
| ReputationRecord | entity + graph | scoped reputation index |
| GraphEdge | graph service | federation-wide indexer |
| ProtocolEvent | ledger chain | append-only event sourcing |

---

## Public Node API (target)

Reference surface for any Entity Node on the public internet:

```http
GET  /.well-known/pocp-node.json
GET  /pocp/health
GET  /pocp/capabilities
POST /pocp/handshake
POST /pocp/invoke
POST /pocp/proofs
POST /pocp/settlements/ack
GET  /pocp/sync
```

Phase A maps many of these to `/api/v1/*` on the reference node; Phase B extracts a standalone `pocp-node` binary.

---

## Technology choices (by phase)

| Concern | Phase A | Phase B+ |
|---------|---------|----------|
| Identity | Entity IDs + federation keys | DID, Ed25519 event signing |
| Transport | HTTPS REST, federation | libp2p, relay, QUIC |
| Storage | Postgres + optional IPFS refs | IPLD, periodic anchor |
| Verification | AI + human advisory | TEE/ZK reserved |
| Reputation | Graph + entity scores | Indexer + decay models |
| Settlement | Internal ledger + proof | Merkle anchor, multi-sig |

---

## Anti-patterns (do not build)

- Central ranking optimizer as protocol core
- Token-first messaging before measurement works
- Single-server “platform” as the only way to join
- Proof without invocation chain
- Settlement without verification trace

---

## CIP reference skeleton

In-memory implementation under `backend/services/cip/` — **does not replace** the production Genesis loop (`services/invocation.py`, wallets, federation). Run the closed-loop demo:

```bash
python backend/scripts/minimum_living_network.py
```

See [MINIMUM-LIVING-NETWORK.md](./MINIMUM-LIVING-NETWORK.md) · [implementation/MINIMUM-LIVING-NETWORK-DEMO.md](./implementation/MINIMUM-LIVING-NETWORK-DEMO.md).

## Next specs to write (backlog)

CIP 12-layer drafts landed in [protocol/README.md](./protocol/README.md). Remaining gaps before `pocp-protocol-spec` split:

```text
P2P-NETWORK-SPEC.md          ← libp2p / DHT (Phase B)
PUBLIC-NODE-PROTOCOL.md      ← wire to standalone pocp-node binary
```

Agent Studio mission: `capability_internet` — see [agent-studio/CAPABILITY-INTERNET-BACKLOG.md](./agent-studio/CAPABILITY-INTERNET-BACKLOG.md).
