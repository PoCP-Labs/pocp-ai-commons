# Public Node Protocol

**Draft v0.2** — Phase A reference node surfaces. Phase B extracts handlers to standalone `pocp-node`.

Related: [NODE-RUNTIME-SPEC.md](./NODE-RUNTIME-SPEC.md) · [ENTITY-NODE-MANIFEST-v0.1.md](./ENTITY-NODE-MANIFEST-v0.1.md)

---

## 1. Instance well-known manifest

Any PoCP instance hosting Entities MUST expose:

```http
GET /.well-known/pocp-node.json
Content-Type: application/json
```

**Phase A implementation:** `backend/main.py` → `build_instance_node_manifest()`.

Frozen contract + validation: `backend/services/node/schemas.py` (`WellKnownInstanceManifestSchema`, `build_instance_endpoints()`, `validate_well_known_instance()`). Per-entity manifests: `validate_well_known_entity()`.

### Response schema

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `protocol` | string | yes | `pocp-node-manifest-v0.2-capability-first` |
| `kind` | string | yes | Always `instance` |
| `instance_id` | string | yes | Env `POCP_NODE_ID` (default `pocp-node-local`) |
| `display_name` | string | yes | Human-readable instance label |
| `facets` | string[] | yes | e.g. `["instance_host"]` |
| `archive_entity_id` | string | yes | Org / federation archive Entity |
| `endpoints` | object | yes | Discovery URLs (see below) |
| `updated_at` | string | yes | ISO-8601 UTC |

### Example (Phase A reference node)

```json
{
  "protocol": "pocp-node-manifest-v0.2-capability-first",
  "kind": "instance",
  "instance_id": "pocp-node-local",
  "display_name": "PoCP AI Commons",
  "facets": ["instance_host"],
  "archive_entity_id": "pocp-org-ai-commons",
  "endpoints": {
    "well_known": "http://127.0.0.1:8000/.well-known/pocp-node.json",
    "health": "http://127.0.0.1:8000/health",
    "capabilities_directory": "http://127.0.0.1:8000/api/v1/capabilities/directory",
    "ledger_verify": "http://127.0.0.1:8000/api/v1/ledger/verify",
    "federation_node": "http://127.0.0.1:8000/api/v1/federation/node"
  },
  "updated_at": "2026-06-02T12:00:00+00:00"
}
```

### Verify locally

```bash
curl -s http://127.0.0.1:8000/.well-known/pocp-node.json | jq .
```

---

## 2. Per-entity node manifest

Active Entities offering capabilities or witness SHOULD publish:

```http
GET /api/v1/entities/{entity_id}/node-manifest
```

**Phase A implementation:** `backend/routers/api.py` · `build_entity_node_manifest()`.

### Response schema

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `protocol` | string | yes | `pocp-node-manifest-v0.2-capability-first` |
| `kind` | string | yes | Always `entity` |
| `entity_id` | string | yes | Entity primary key |
| `entity_type` | string | yes | Ontology slug (14 types) |
| `display_name` | string | yes | Entity name |
| `description` | string | no | Entity description |
| `status` | string | yes | Entity status |
| `facets` | string[] | yes | `consumer`, `capability_provider`, `compute_provider`, `witness`, `instance_host` |
| `capabilities` | object[] | yes | Registry + compute_profile offers |
| `endpoints` | object | yes | Entity-scoped URLs |
| `wallet_id` | string | no | When Entity has wallet |
| `witness` | object | no | When facet includes `witness` |
| `compute_profile` | object | no | When compute provider |
| `updated_at` | string | yes | ISO-8601 UTC |

### Example (capability provider)

```json
{
  "protocol": "pocp-node-manifest-v0.2-capability-first",
  "kind": "entity",
  "entity_id": "pocp-entity-local-compute",
  "entity_type": "compute_node",
  "display_name": "Local Compute Node",
  "status": "active",
  "facets": ["capability_provider", "compute_provider"],
  "capabilities": [
    {
      "capability_id": "pocp-cap-local-compute-gpu",
      "capability_type": "gpu_inference",
      "name": "Local GPU/CPU inference",
      "unit": "gpu_second",
      "exchange_kind": "compute",
      "availability": "available"
    }
  ],
  "endpoints": {
    "manifest": "http://127.0.0.1:8000/api/v1/entities/pocp-entity-local-compute/node-manifest",
    "entity": "http://127.0.0.1:8000/api/v1/entities/pocp-entity-local-compute",
    "capabilities": "http://127.0.0.1:8000/api/v1/registry/capabilities?entity_id=pocp-entity-local-compute",
    "compute_register": "http://127.0.0.1:8000/api/v1/compute/entities/pocp-entity-local-compute/register"
  },
  "updated_at": "2026-06-02T12:00:00+00:00"
}
```

Entity manifests are seeded after platform catalog bootstrap — see [NODE-RUNTIME-SPEC.md §4](./NODE-RUNTIME-SPEC.md#4-entity-catalog-linkage-ci-1--ci-2).

---

## 3. Public Node API (Phase B target)

Phase A maps many routes to `/api/v1/*`. **Phase A shim (implemented):** `backend/routers/pocp_public.py` exposes:

```http
GET  /pocp/node
GET  /pocp/health
GET  /pocp/capabilities
GET  /pocp/protocol
GET  /pocp/sync
POST /pocp/handshake
POST /pocp/invoke
POST /pocp/proofs
POST /pocp/settlements/ack
```

Phase B standalone binary extracts handlers to `pocp-node` without changing semantics.

**Operator manifest:** `GET /api/v1/intelligence/protocol/federation` includes `public_node`, `exchange_import`, and `metered_bindings` (see [BINDING-TO-DIALOGUE.md](./BINDING-TO-DIALOGUE.md)). Frozen endpoint keys: `backend/services/node/schemas.py` · `backend/services/protocol/schemas.py`.

---

## 4. Node modes

```text
direct_public
reverse_proxy
relay
hosted
offline_light
```

Default for platform infrastructure nodes: `hosted`.

---

## 5. Node registration API (Phase A)

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/api/v1/nodes/register` | Upsert NodeProfile for Entity |
| `POST` | `/api/v1/nodes/{node_id}/heartbeat` | Heartbeat |
| `GET` | `/api/v1/nodes/discover` | Filter by capability_type / node_type |

Persistence: `backend/services/node/store.py` · contract: `backend/services/node/schemas.py`.

---

## 6. Anti-patterns

- Instance manifest without `archive_entity_id`
- NodeProfile without backing Entity row
- Commercial ranking fields in public manifest (`risk_weights`, `optimizer_private`, etc.) — **Open Core forbidden**
