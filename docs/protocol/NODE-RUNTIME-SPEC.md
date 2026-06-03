# Node Runtime Spec

**Layer 2** — NodeProfile binds an [Entity](./ENTITY-LAYER-SPEC.md) to network connectivity, discovery URLs, and heartbeat state.

Parent: [POCP-NETWORK-ARCHITECTURE.md](../POCP-NETWORK-ARCHITECTURE.md) · Manifest: [ENTITY-NODE-MANIFEST-v0.1.md](./ENTITY-NODE-MANIFEST-v0.1.md) · Well-known: [PUBLIC-NODE-PROTOCOL.md](./PUBLIC-NODE-PROTOCOL.md)

---

## 1. Entity vs NodeProfile

| Object | Storage | Purpose |
|--------|---------|---------|
| **Entity** | `entities` table | Identity, type, wallet, reputation |
| **NodeProfile** | `node_profiles` table | How this Entity connects to the network |
| **Node manifest** | JSON (well-known + per-entity API) | What this Entity **offers** (capabilities, facets) |

An Entity without a NodeProfile is a **passive neuron** (consumer-only).  
An Entity with NodeProfile + manifest is an **active neuron** (provider, witness, archive, etc.).

---

## 2. Node types

```text
light
service
compute
verifier
reviewer
relay
indexer
governance
treasury
```

Maps to `NodeType` enum in `backend/models/node_profile.py`.

---

## 3. NodeProfile schema (frozen v0.1)

Open-core contract: `backend/services/node/schemas.py` · boundary protocols: `backend/services/node/base.py` · persistence: `backend/models/node_profile.py`.

**Catalog linkage:** Entity IDs in `backend/services/entity/schemas.py` · node-type mapping in `CATALOG_NODE_TYPE_BY_ENTITY` and `catalog_node_specs(backend_url=…)` — consumed by `entity_catalog._ensure_node_profiles()`.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `node_id` | string | yes | Primary key; stable after first register |
| `entity_id` | string | yes | FK → `entities.id`; **one profile per Entity** |
| `node_type` | enum | yes | See §2 |
| `did` | string | no | Default `did:pocp:{entity_id}` |
| `public_key` | string | no | Phase B — event signing |
| `base_url` | string | no | HTTPS origin for public endpoints |
| `p2p_address` | string | no | Phase B — libp2p multiaddr |
| `health_url` | string | no | Default `{base_url}/pocp/health` |
| `node_mode` | enum | no | Default `hosted` |
| `status` | enum | no | `registered` \| `active` \| `offline` \| `suspended` |
| `protocol_version` | string | yes | Default `pocp-node-v0.1` |
| `published_capabilities` | string[] | no | Capability type slugs for discovery |
| `metadata` | object | no | Opaque host hints (non-commercial) |
| `last_heartbeat_at` | datetime | no | Updated on heartbeat |
| `created_at` | datetime | yes | Server-managed |
| `updated_at` | datetime | yes | Server-managed |

### Node modes

```text
direct_public
reverse_proxy
relay
hosted
offline_light
```

### Status transitions

```text
registered → active     (heartbeat or first successful health check)
active     → offline    (missed heartbeat threshold)
active     → suspended  (governance / operator)
offline    → active     (heartbeat resume)
```

---

## 4. Entity catalog linkage (CI-1 → CI-2)

Platform bootstrap in `backend/services/entity_catalog.py` idempotently:

1. Registers **14 ontology entity types** including infrastructure nodes (compute, verifier, reviewer, sponsor, treasury, workflow).
2. Seeds capability registry rows for genesis + infrastructure entities.
3. Creates **NodeProfile** rows for infrastructure entities via `register_node()`.
4. Cross-links stable IDs in org/Rain metadata (`compute_node_id`, `verifier_node_id`, etc.).

Stable infrastructure entity IDs (must not drift):

| Entity ID | Entity type | Node type |
|-----------|-------------|-----------|
| `pocp-entity-local-compute` | `compute_node` | `compute` |
| `pocp-entity-local-verifier` | `verifier_node` | `verifier` |
| `pocp-entity-bob-reviewer` | `reviewer_node` | `reviewer` |
| `pocp-entity-rain-sponsor` | `sponsor` | `service` |
| `pocp-entity-protocol-treasury` | `protocol_treasury` | `treasury` |
| `pocp-entity-study-workflow` | `workflow` | — (Entity only; no NodeProfile required) |

Audit command:

```bash
python backend/scripts/audit_entities.py --repair
```

---

## 5. Public endpoints (derived)

When `base_url` is set, derived URLs (Phase A maps many to `/api/v1/*` on the reference node):

| Surface | Target path |
|---------|-------------|
| Instance manifest | `GET /.well-known/pocp-node.json` |
| Entity manifest | `GET /api/v1/entities/{entity_id}/node-manifest` |
| Health | `GET /pocp/health` (Phase B) · `/health` (Phase A) |
| Capabilities | `GET /pocp/capabilities` (Phase B) · `/api/v1/registry/capabilities` (Phase A) |
| Invoke | `POST /pocp/invoke` |
| Proofs | `POST /pocp/proofs` |
| Settlement ack | `POST /pocp/settlements/ack` |

Implementation: `backend/services/node/store.py` · `backend/services/node_manifest.py` · `backend/main.py`.

---

## 6. Heartbeat

Nodes SHOULD emit heartbeat at least every **120s** when active.

| API | Purpose |
|-----|---------|
| `POST /api/v1/nodes/{node_id}/heartbeat` | Update `last_heartbeat_at`, set `status=active` |
| CIP in-memory | `backend/services/cip/node/heartbeat.py` |

---

## 7. CIP reference skeleton

In-memory mirror under `backend/services/cip/node/` for closed-loop demos — does **not** replace Postgres `node_profiles`.

```bash
python backend/scripts/minimum_living_network.py
```

---

## 8. Phase gaps (explicit)

| Gap | Phase | Owner track |
|-----|-------|-------------|
| Ed25519 signed manifests | B | CI-3 Identity |
| libp2p / DHT discovery | B | CI-5 Discovery |
| Standalone `pocp-node` binary | B | PUBLIC-NODE-PROTOCOL |
| Commercial node ranking | — | **Forbidden** in Open Core |
