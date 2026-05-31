# Entity Management on the Platform

How PoCP AI Commons **defines**, **registers**, and **operates** Entities — the network subjects that participate in verified contribution.

**See also:** [ENTITY-ONTOLOGY.md](./ENTITY-ONTOLOGY.md) (types & roles) · [PROTOCOL.md](./PROTOCOL.md) · [GENESIS.md](../GENESIS.md)

---

## 1. Three layers

| Layer | What you manage | Where |
|-------|-----------------|--------|
| **Definition** | Nine `entity_type` values, metadata contracts, participant roles | `docs/ENTITY-ONTOLOGY.md`, `backend/intelligence/entity_ontology.py` |
| **Registration** | Creating rows in `entities`, linking owner/creator, optional Skill/Agent rows | `backend/services/entity_register.py`, API below |
| **Runtime** | Status, participation in contributions, wallet/reputation/graph | Contributions, ledger, graph APIs |

**Rule:** `UserAccount` is login only. Every contributor is an **Entity** (usually `human`).

---

## 2. Management tiers

| Tier | Examples | How to change |
|------|----------|----------------|
| **L0 Genesis** | Lumen-0, DeSui, Clarion-0, Rain | `backend/genesis.py` → `ensure_genesis_entities()` on startup; **not** via PATCH API |
| **L1 Organization** | PoCP AI Commons | `POST /api/v1/organizations` (authenticated) |
| **L2 Human** | Rain, Bob, dev-login users | Auto on `POST /api/v1/auth/dev-login` or GitHub OAuth |
| **L3 Capability** | Agent, Skill, Tool, Dataset, Workflow | Typed register endpoints; `owner_id` / `maintainer_id` = your human entity |
| **L4 Event roles** | creator, witness, verifier, … | Declared per contribution; ontology validation on submit |

---

## 3. API reference

### List & search

```http
GET /api/v1/entities
GET /api/v1/entities?entity_type=llm
GET /api/v1/entities?status=active
GET /api/v1/entities?owner_id=<uuid>
GET /api/v1/entities?q=lumen
GET /api/v1/entities?genesis_only=true
```

### Read one + ontology slice

```http
GET /api/v1/entities/{id}
GET /api/v1/entities/{id}/ontology
GET /api/v1/entities/ontology
```

### Register (create)

| Method | Path | Auth |
|--------|------|------|
| POST | `/api/v1/entities` | Open (generic type) |
| POST | `/api/v1/entities/tool` | Bearer; maintainer = self |
| POST | `/api/v1/entities/dataset` | Bearer; maintainer = self |
| POST | `/api/v1/entities/workflow` | Bearer; maintainer = self |
| POST | `/api/v1/agents` | Bearer; maintainer = self |
| POST | `/api/v1/skills` | Bearer; maintainer = self |
| POST | `/api/v1/organizations` | Bearer | 

New humans: **do not** POST `/entities` manually — use auth endpoints.

### Update (owner- or org-proxy-scoped)

```http
PATCH /api/v1/entities/{id}
Authorization: Bearer <token>
Content-Type: application/json

{
  "description": "Updated description",
  "status": "inactive",
  "metadata": { "capabilities": ["summarize"] }
}
```

- Allowed: `name`, `description`, `status` (`active` | `inactive` | `pending`), `metadata` (merged).
- **Forbidden:** changing Genesis entity IDs (403).
- **Authorized actors:** entity `owner_id` or `creator_id`, or the organization's `governance_proxy_id` when `owner_id` is an organization.

Deactivating (`inactive`) keeps history in ledger/graph; capability execution should reject inactive entities.

### Pending review (governance queue)

Imported or manually registered capabilities may start as `pending`.

```http
GET /api/v1/entity-reviews/pending
Authorization: Bearer <token>
```

Returns pending entities the caller may govern (owner, creator, or org proxy).

```http
POST /api/v1/entities/{id}/review
Authorization: Bearer <token>
Content-Type: application/json

{ "action": "approve", "feedback": "Ready for network use." }
```

Actions: `approve` → `active`, `reject` → `inactive`. Review metadata is stored under `entity.metadata.review`.

---

## 4. Accountability checklist

When operating the platform:

1. **Non-human entities** must have `owner_id` → human or organization.
2. **LLM / Agent witnesses** advise only; finalization follows published policy (see PROTOCOL).
3. **Participant roles** must fit entity type when `POCP_VALIDATE_PARTICIPANT_ONTOLOGY=true` (default).
4. **Genesis entities** are refreshed on boot; do not delete their IDs from production DB without a protocol migration plan.

---

## 5. Operator workflows

### Onboard a human

1. User hits **Dev Login** or GitHub OAuth.
2. System creates `UserAccount` + `Entity(human)` + `Wallet` + starter AI Credits.
3. User registers Agent/Skill/Tool under their entity id as maintainer.

### Register a community Tool (MCP)

```bash
curl -X POST http://localhost:8000/api/v1/entities/tool \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "R Docs MCP",
    "description": "Matrix docs lookup",
    "maintainer_id": "<your-human-entity-id>",
    "tool_kind": "mcp",
    "mcp_server": "r-docs",
    "capabilities": ["search", "fetch"]
  }'
```

### Retire a Skill

```bash
curl -X PATCH http://localhost:8000/api/v1/entities/<skill-entity-id> \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status": "inactive"}'
```

### Approve a pending Tool (Bob as org governance proxy)

```bash
curl http://localhost:8000/api/v1/entity-reviews/pending \
  -H "Authorization: Bearer $BOB_TOKEN"

curl -X POST http://localhost:8000/api/v1/entities/<pending-id>/review \
  -H "Authorization: Bearer $BOB_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"action":"approve","feedback":"Verified for pilot."}'
```

### Audit the network

- Dashboard → **Entities** tab (filter by type/status).
- `GET /api/v1/graph` for contribution topology.
- `GET /api/v1/entities/{id}/ontology` for roles + metadata contract.

---

## 6. Code map

| Module | Role |
|--------|------|
| `backend/models/entity.py` | ORM + enums |
| `backend/genesis.py` | L0 specs + `GENESIS_ENTITY_IDS` |
| `backend/services/entity_register.py` | Typed registration |
| `backend/services/entity_management.py` | List filters + PATCH rules |
| `backend/routers/api.py` | HTTP surface |
| `frontend/src/EntityDetail.jsx` | Entity drill-down UI |

---

*PoCP begins with contribution — every Entity exists to make that contribution visible, verifiable, and valuable.*
