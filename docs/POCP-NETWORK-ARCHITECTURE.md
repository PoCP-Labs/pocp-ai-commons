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
| 1 | **Entity** | [01-ENTITY-REGISTRY.md](./architecture/01-ENTITY-REGISTRY.md), [ENTITY-SCHEMA-v0.3.md](./protocol/ENTITY-SCHEMA-v0.3.md) | `models/entity.py`, `services/entity_register.py`, `services/entity_catalog.py` | **14 types seeded**; ownership bootstrap |
| 2 | **Node** | [ENTITY-NODE-MANIFEST-v0.1.md](./protocol/ENTITY-NODE-MANIFEST-v0.1.md), [COMPUTE-FEDERATION-SPEC.md](./COMPUTE-FEDERATION-SPEC.md) | `services/compute_profile.py`, `services/compute_registry.py`, `config/compute_nodes.yaml` | Compute + federation nodes; **no generic NodeProfile table yet** |
| 3 | **Identity** | [TRUST-POLICY-BUNDLE.md](./protocol/TRUST-POLICY-BUNDLE.md), federation crypto | `services/federation_*.py`, ledger signatures | Federation import signatures; **DID/VC not yet** |
| 4 | **Capability** | [02-CAPABILITY-REGISTRY.md](./architecture/02-CAPABILITY-REGISTRY.md), [CAPABILITY-SCHEMA-v0.3.md](./protocol/CAPABILITY-SCHEMA-v0.3.md) | `services/capability/`, `routers/capability_registry.py` | Registry + execute path; **public node manifest partial** |
| 5 | **Discovery** | [03-NEURAL-ROUTING.md](./architecture/03-NEURAL-ROUTING.md), [ENTITY-DIALOGUE-PROTOCOL.md](./protocol/ENTITY-DIALOGUE-PROTOCOL.md) | `services/neural/rule_based_router.py`, federation peers | Rule-based routing; **no DHT/libp2p** |
| 6 | **Invocation** | [04-INVOCATION-LEDGER.md](./architecture/04-INVOCATION-LEDGER.md), [INVOCATION-SCHEMA-v0.3.md](./protocol/INVOCATION-SCHEMA-v0.3.md) | `services/invocation.py`, `services/invocation_ledger.py` | Traces + **invocation_ref** on exchanges (PR-A) |
| 7 | **Proof** | [05-VERIFICATION-PROOF.md](./architecture/05-VERIFICATION-PROOF.md) | `services/proof.py`, export routers | Portable proof packets + Merkle |
| 8 | **Verification** | Same + challenge flow | `services/verifiers/`, `services/contribution_dispute.py` (PR-B) | Multi-verifier advisory; challenge/appeal WIP |
| 9 | **Settlement** | [07-SETTLEMENT-LAYER.md](./architecture/07-SETTLEMENT-LAYER.md) | `services/exchange_spine.py`, `services/settlement_policy.py` | Exchange spine + policy tags |
| 10 | **Reputation** | [08-REPUTATION-GOVERNANCE.md](./architecture/08-REPUTATION-GOVERNANCE.md), [09-NEURAL-GRAPH.md](./architecture/09-NEURAL-GRAPH.md) | `services/graph.py`, entity reputation fields | Graph UI + scores; **event-sourced reputation backlog** |
| 11 | **Governance** | [08-REPUTATION-GOVERNANCE.md](./architecture/08-REPUTATION-GOVERNANCE.md) | org foundation, reviewer queue, policy bot | Demo governance proxy; **PIP process draft** |
| 12 | **Economy** | [06-TOKEN-MEASUREMENT.md](./architecture/06-TOKEN-MEASUREMENT.md) | wallets, CP/AIC/CC, `services/token_measurement/` | Internal metering only — **no public token** |

Legend: **bold** = materially present in tree; plain = partial; “not yet” = spec-only.

---

## Data objects (target v1)

| Object | Table / service today | Gap |
|--------|----------------------|-----|
| Entity | `entities` | — |
| NodeProfile | metadata + compute_profile | dedicated `node_profiles` table |
| Capability | `entity_capabilities` | public `/.well-known/pocp-node.json` |
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

## Next specs to write (backlog)

When splitting to `pocp-protocol-spec`:

```text
NODE-RUNTIME-SPEC.md
PUBLIC-NODE-PROTOCOL.md
P2P-NETWORK-SPEC.md
DID-SIGNATURE-SPEC.md
VERIFICATION-NETWORK-SPEC.md
REPUTATION-GRAPH-SPEC.md (extend 08)
GOVERNANCE-SPEC.md (extend 08)
PROTOCOL-ECONOMY-SPEC.md (extend 06)
```

Agent Studio mission: `capability_internet` — see [agent-studio/CAPABILITY-INTERNET-BACKLOG.md](./agent-studio/CAPABILITY-INTERNET-BACKLOG.md).
