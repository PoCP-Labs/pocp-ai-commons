# Provider quickstart — manifest to quoteable directory

**Scope:** CIP-P2.3 · **Time:** ~15 minutes · **Goal:** YAML manifest → Entity + capability registry → public directory → quote probe.

Parent: [PUBLIC-NODE-PROTOCOL.md](../protocol/PUBLIC-NODE-PROTOCOL.md) · Template: [`examples/provider.manifest.example.yaml`](./examples/provider.manifest.example.yaml) · Script: [`scripts/provider_bootstrap.py`](../../scripts/provider_bootstrap.py)

---

## What you get

| Step | Outcome | API |
|------|---------|-----|
| 1 | Provider Entity registered | `GET /api/v1/entities/{entity_id}` |
| 2 | Capabilities in registry | `GET /api/v1/registry/capabilities?entity_id=…` |
| 3 | Listed in public directory | `GET /api/v1/capabilities/directory` · `GET /pocp/capabilities` |
| 4 | Quoteable via dialogue | `POST /api/v1/federation/dialogue` (`kind: quote`) |

The bootstrap script performs steps 1–4 idempotently from a single YAML file.

---

## Prerequisites (2 min)

- Python 3.11+ with backend deps installed (`pip install -r backend/requirements.txt`)
- Local backend running **or** SQLite DB path configured in `backend/.env`

**Quick stack (Option A from [LOCAL-SETUP.md](../LOCAL-SETUP.md)):**

```bash
cd backend
cp .env.example .env
# DATABASE_URL=sqlite:///./data/pocp.db
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

Leave the server running in one terminal; use a second terminal for the steps below.

---

## Step 1 — Copy the example manifest (1 min)

```bash
cp docs/public-node/examples/provider.manifest.example.yaml my-provider.yaml
```

Edit `my-provider.yaml` as needed:

| Field | Required | Notes |
|-------|----------|-------|
| `provider.entity_type` | yes | Ontology slug: `skill`, `tool`, `agent`, `compute_node`, … |
| `provider.name` | yes | Display name |
| `provider.entity_id` | no | Stable portable ID (recommended for re-runs) |
| `provider.owner_id` | no | Defaults to `pocp-entity-rain` (demo human) |
| `capabilities[]` | yes | At least one registry row |
| `capabilities[].capability_type` | yes | e.g. `coding`, `reasoning`, `gpu_inference` |
| `capabilities[].unit` | yes | e.g. `skill_invocation`, `llm_token`, `gpu_second` |
| `quote_test.from_entity_id` | no | Human Entity for quote probe (must have wallet) |

Reference capability types and units: [`backend/models/capability.py`](../../backend/models/capability.py).

Align with the public skill node template:

```bash
curl -s http://127.0.0.1:8000/api/v1/federation/skill-node-template | jq .default_capability
```

---

## Step 2 — Bootstrap provider (2 min)

From repo root:

```bash
python scripts/provider_bootstrap.py my-provider.yaml --quote --json
```

Expected output (abbreviated):

```json
{
  "valid": true,
  "bootstrap": {
    "entity_id": "pocp-entity-demo-code-review",
    "entity_created": true,
    "capabilities_created": ["pocp-cap-demo-code-review"]
  },
  "checks": {
    "directory": { "ok": true, "detail": "directory lists 1 offer(s) for …" },
    "quote": { "ok": true, "detail": "quote accepted (exchange_id=…, cost=5.0)" }
  }
}
```

Re-running the same manifest is **idempotent** — existing Entity and capability IDs are skipped.

**With live HTTP check** (backend must be running):

```bash
python scripts/provider_bootstrap.py my-provider.yaml --verify-url http://127.0.0.1:8000 --quote
```

---

## Step 3 — Verify directory (3 min)

**Registry search:**

```bash
curl -s "http://127.0.0.1:8000/api/v1/registry/capabilities?entity_id=pocp-entity-demo-code-review" | jq .
```

**Public directory** (marketplace view — compute + capability providers):

```bash
curl -s "http://127.0.0.1:8000/api/v1/capabilities/directory?capability_type=coding" | jq .
curl -s "http://127.0.0.1:8000/pocp/capabilities?capability_type=coding" | jq .
```

Confirm your `provider_entity_id` appears in `items[]` with `source: registry`.

**Entity node manifest:**

```bash
curl -s "http://127.0.0.1:8000/api/v1/entities/pocp-entity-demo-code-review/node-manifest" | jq .
```

Expect `facets` to include `capability_provider` and `capabilities[]` to list your offers.

---

## Step 4 — Quote probe (3 min)

Pre-invoke quote binds an `exchange_id` for the invoke chain ([ENTITY-DIALOGUE-PROTOCOL.md](../protocol/ENTITY-DIALOGUE-PROTOCOL.md)):

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/federation/dialogue \
  -H "Content-Type: application/json" \
  -d '{
    "schema": "pocp.entity_dialogue.v0.1",
    "dialogue_id": "dlg_provider_quickstart_001",
    "kind": "quote",
    "from": {"entity_id": "pocp-entity-rain"},
    "to": {"entity_id": "pocp-entity-demo-code-review"},
    "payload": {
      "quote_action": "capability_invoke",
      "estimated_cost": 5.0
    }
  }' | jq .
```

Success: `"status": "accepted"` and `"quote": { "allowed": true, … }`.

Public-node alias (same semantics):

```bash
curl -s -X POST http://127.0.0.1:8000/pocp/invoke \
  -H "Content-Type: application/json" \
  -d '{ … same envelope … }' | jq .
```

---

## Step 5 — Federation discover (optional, 4 min)

If you run the [federation demo](../LOCAL-SETUP.md#option-c--phase-a-one-command-recommended-for-acceptance):

```bash
docker compose -f docker-compose.federation.yml up -d --build
python scripts/provider_bootstrap.py my-provider.yaml --verify-url http://127.0.0.1:8100 --quote
```

Peer discover + handshake:

```bash
curl -s -X POST http://127.0.0.1:8100/api/v1/federation/peers/handshake \
  -H "Content-Type: application/json" \
  -d '{"peer_base_url": "http://127.0.0.1:8101", "capability_type": "coding"}' | jq .
```

Cross-node quote→invoke acceptance: [`scripts/cross_node_exchange_acceptance.py`](../../scripts/cross_node_exchange_acceptance.py).

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `quote rejected: quote requires from entity to be human` | Set `quote_test.from_entity_id` to a human Entity (e.g. `pocp-entity-rain`) |
| `quote not allowed` | Billing anchor needs AIC balance — run `python backend/scripts/audit_entities.py --full-seed --repair` once |
| Provider missing from directory | Confirm `availability: available` and Entity `status: active` |
| `Invalid CapabilityType` | Use enum values from `backend/models/capability.py` (`coding`, not `code_review`) |
| HTTP directory check fails | Backend not running or stale DB — restart uvicorn after bootstrap |

**Preflight for HTTPS operators:** [`backend/scripts/public_node_preflight.py`](../../backend/scripts/public_node_preflight.py)

---

## Manifest schema (`pocp.provider_manifest.v0.1`)

```yaml
schema: pocp.provider_manifest.v0.1
spec_version: "0.1"
provider:
  entity_id: pocp-entity-my-skill
  entity_type: skill
  name: My Skill
  description: Callable capability surface
  owner_id: pocp-entity-rain
capabilities:
  - capability_id: pocp-cap-my-skill
    capability_type: coding
    name: Code review
    unit: skill_invocation
    base_price: 5.0
    accepted_units: [AIC]
quote_test:
  from_entity_id: pocp-entity-rain
  quote_action: capability_invoke
  estimated_cost: 5.0
```

---

## Related docs

- [PUBLIC-NODE-PROTOCOL.md](../protocol/PUBLIC-NODE-PROTOCOL.md) — instance + entity manifests
- [FEDERATION-DISCOVERY.md](../FEDERATION-DISCOVERY.md) — peer manifest + skill-node template
- [CAPABILITY-INTERNET-GAP-PR-PLAN.md](../implementation/CAPABILITY-INTERNET-GAP-PR-PLAN.md) — PR-2.3 backlog entry
- [ENTITY-ONTOLOGY.md](../ENTITY-ONTOLOGY.md) — entity types and portable IDs

---

## Acceptance checklist

- [ ] `python scripts/provider_bootstrap.py --quote` exits 0
- [ ] Provider appears in `GET /api/v1/capabilities/directory`
- [ ] Quote dialogue returns `allowed: true`
- [ ] Entity node manifest lists `capability_provider` facet
