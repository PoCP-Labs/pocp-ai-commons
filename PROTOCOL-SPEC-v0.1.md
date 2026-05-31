# PoCP Protocol Spec V0.1

**Minimal protocol specification for PoCP AI Commons implementation.**

This document is the builder-facing contract. For extended schema details see [docs/SCHEMA.md](./docs/SCHEMA.md). For conceptual protocol notes see [docs/PROTOCOL.md](./docs/PROTOCOL.md).

---

## 1. Scope

V0.1 proves **one loop**:

```text
Entity registers → receives starter AI Credits
  → completes task → submits contribution
  → AI advisory verify → human approve
  → CP + AI Credits issued → ledger written
```

**In scope:** Human, Agent, Skill entities; tasks; contributions; verification; wallets; reputation; ledger.

**Out of scope:** Tokens, on-chain anchoring, decentralized governance, public marketplace, unlimited free AI.

### 1.1 Native Technology Principle

PoCP is not a bundle of unrelated technologies.

It may use web APIs, databases, LLMs, hashes, ledgers, and graph views, but V0.1 implementation must serve PoCP-native primitives:

```text
Entity
Contribution Event
Contribution Participant
Evidence Hash
Human-AI Verification State
Contribution Proof Packet
Contribution Graph
Contribution-to-Rights Conversion
Ledger Memory
```

The goal is not to assemble:

```text
LLM API + task board + points + graph UI
```

The goal is to make contribution itself a portable, verifiable protocol object.

---

## 2. Core Objects

### 2.1 Entity

First-class intelligent subject.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `id` | UUID | auto | |
| `entity_type` | enum | yes | See §2.2 |
| `name` | string | yes | |
| `description` | text | no | |
| `owner_id` | UUID | conditional | Required for non-human entities |
| `creator_id` | UUID | no | Who registered |
| `status` | enum | yes | `active`, `inactive`, `pending` |
| `metadata` | JSON | no | Type-specific config |

### 2.2 Entity Types

| Type | V0.1 | Notes |
|------|------|-------|
| `human` | ✅ | Contributor, reviewer, owner |
| `agent` | ✅ | Task assistant |
| `skill` | ✅ | Reusable capability |
| `llm` | provider | Used in verification; not full citizen |
| `tool` | reserved | |
| `dataset` | reserved | |
| `workflow` | reserved | |
| `organization` | reserved | |
| `community` | reserved | |

### 2.3 Task

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID | |
| `title` | string | |
| `description` | text | Acceptance criteria |
| `sponsor_id` | UUID → Entity | |
| `status` | enum | `open`, `in_progress`, `completed`, `closed` |
| `reward_cp` | float | Suggested CP on approval |
| `reward_credits` | float | Suggested AI Credits on approval |

### 2.4 Contribution Event

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID | |
| `task_id` | UUID | |
| `primary_entity_id` | UUID | Main contributor (usually human) |
| `contribution_type` | string | e.g. `code`, `review`, `knowledge` |
| `description` | text | |
| `evidence` | JSON | Links, artifacts, content hash |
| `status` | enum | See §3 |

### 2.5 Contribution Participant

Many-to-many link between contribution and entities.

| Field | Type | Notes |
|-------|------|-------|
| `entity_id` | UUID | |
| `role` | enum | See §2.6 |
| `weight` | float | 0.0–1.0, sum ≈ 1.0 |
| `evidence` | JSON | Role-specific proof |

### 2.6 Participant Roles

`creator`, `executor`, `reviewer`, `verifier`, `tool_provider`, `data_provider`, `skill_provider`, `model_provider`, `coordinator`, `sponsor`

V0.1 minimum: `creator`, `executor`, `skill_provider`

### 2.7 Wallet

| Field | Type | Notes |
|-------|------|-------|
| `entity_id` | UUID | One wallet per entity |
| `cp_balance` | float | Contribution Points (non-transferable) |
| `ai_credits` | float | AI usage balance |

### 2.8 Reputation Score

| Field | Type | Notes |
|-------|------|-------|
| `entity_id` | UUID | |
| `score` | float | Cumulative; decay in future versions |
| `category` | string | `human`, `agent`, `skill` |

### 2.9 Ledger Record

Append-only audit event.

| Field | Type | Notes |
|-------|------|-------|
| `contribution_id` | UUID | |
| `event_type` | string | e.g. `contribution_approved` |
| `payload` | JSON | Immutable snapshot |

---

## 3. Contribution State Machine

```text
draft
  → submitted          (contributor submits)
  → ai_verified        (AI advisory review recorded)
  → approved           (entity-equal policy finalizes; any Entity type may delegate)
  → rejected           (policy/finalizer rejects; terminal)

ai_verified may also → rejected
submitted may skip ai_verified only in dev mode (NOT in production)
```

**Production rule:** `approved` requires prior `ai_verified`.

**AI rule:** AI verification updates status to `ai_verified` but **never** to `approved`.

---

## 4. Verification

### 4.1 AI Advisory Review

| Field | Type | Notes |
|-------|------|-------|
| `contribution_id` | UUID | |
| `model_provider` | string | e.g. `gpt-4o`, `deepseek` |
| `score` | float | 0.0–1.0 overall |
| `feedback` | text | Human-readable rationale |
| `passed` | boolean | Advisory only |
| `details` | JSON | Optional structured rubric |

Recommended `details` shape:

```json
{
  "task_match": 0.85,
  "quality": 0.80,
  "evidence_score": 0.90,
  "risk_flags": [],
  "suggested_cp": 10,
  "suggested_credits": 100
}
```

### 4.2 Human Review

| Field | Type | Notes |
|-------|------|-------|
| `contribution_id` | UUID | |
| `reviewer_id` | UUID | Must be `human` entity |
| `approved` | boolean | Final decision |
| `feedback` | text | Required on reject |

---

## 5. Rewards

On **human approval**:

| Recipient | CP | AI Credits | Reputation |
|-----------|-----|------------|------------|
| Primary human entity | ✅ | ✅ | ✅ |
| Agent participants | — | — | ✅ (weighted) |
| Skill participants | — | — | ✅ (weighted) |

Default V0.1 values (override per task):

| Event | CP | AI Credits |
|-------|-----|------------|
| Registration grant | 0 | 100 |
| Small task approval | 10 | 50 |
| Medium task approval | 25 | 150 |
| Large task approval | 50 | 300 |

All issuances create `credit_transactions` and `ledger_records`.

### 5.1 Rights Rules (`pocp.rights_rules.v0.1`)

Instance config: `backend/config/pocp_rewards.yaml`

| Field | Meaning |
|-------|---------|
| `spec_version` | Rules version embedded in proof packets |
| `rights.bc` | AI Credits — spendable, non-transferable |
| `rights.cp` | Contribution Points — non-spendable proof |
| `contribution_defaults` | Base amounts per entity type × role weight |

API: `GET /api/v1/intelligence/protocol/rights-rules`

### 5.2 Contribution-to-Rights Conversion

Proof block schema: `pocp.contribution_to_rights_conversion.v0.1`

Contains `planned_allocations` (recomputable from rules) and `applied_rewards` (ledger snapshot on approval).

### 5.3 Capability Receipt (`pocp.capability_receipt.v0.1`)

Per **InvocationTrace** step — records capability kind, endpoint, optional request/response hashes.

Stored in `invocation_steps.metadata`; exported in agent receipts and proof packets.

See [docs/VALUE-EXCHANGE-PROTOCOL.md](./docs/VALUE-EXCHANGE-PROTOCOL.md).

---

## 6. REST API (V0.1)

Base path: `/api/v1`

### Read

| Method | Path | Description |
|--------|------|-------------|
| GET | `/entities` | List entities |
| GET | `/entities/{id}` | Get entity |
| GET | `/skills` | List skills |
| GET | `/agents` | List agents |
| GET | `/tasks` | List tasks |
| GET | `/contributions` | List contributions |
| GET | `/contributions/{id}` | Get contribution |
| GET | `/wallets` | List wallets |
| GET | `/reputation` | List reputation scores |
| GET | `/ledger` | List ledger records |
| GET | `/ledger/export` | Export ledger (asc, optional `since`) |
| GET | `/ledger/verify` | Verify hash chain integrity |
| GET | `/ledger/anchor` | Merkle root anchor (+ optional node signature) |
| GET | `/entities/{id}/portable` | Portable entity + reputation export |
| GET | `/contributions/{id}/proof` | Portable contribution proof packet |
| GET | `/graph` | Contribution graph (nodes + edges) |

### Write

| Method | Path | Description |
|--------|------|-------------|
| POST | `/entities` | Register entity (+ auto-create wallet for humans) |
| POST | `/tasks` | Create task |
| POST | `/contributions` | Submit contribution |
| POST | `/contributions/{id}/auto-verify` | Multi-witness verify + optional auto-finalize |
| POST | `/contributions/{id}/finalize` | Traceable finalization (any Entity type per policy) |
| POST | `/contributions/{id}/approve` | Legacy alias for `/finalize` |

### Health

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Service status |

### Federation (v0.2)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/federation/node` | Node identity and public endpoints |
| GET | `/federation/trust` | Trusted peer nodes |
| GET | `/federation/imports` | List imported federated contributions |
| POST | `/federation/import` | Import event by portable payload (reputation only) |
| GET | `/federation/reputation` | Federated reputation by `portable_id` |
| POST | `/federation/import-proof` | Import from contribution proof packet |

See [docs/FEDERATION-v0.1.md](./docs/FEDERATION-v0.1.md).

---

## 7. Example Flow (curl)

```bash
# 1. Register human
curl -X POST http://localhost:8000/api/v1/entities \
  -H "Content-Type: application/json" \
  -d '{"entity_type":"human","name":"Rain"}'

# 2. Create task
curl -X POST http://localhost:8000/api/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{"title":"Write R tutorial","description":"Create 5 exercises","sponsor_id":"<sponsor-uuid>"}'

# 3. Submit contribution
curl -X POST http://localhost:8000/api/v1/contributions \
  -H "Content-Type: application/json" \
  -d '{
    "task_id":"<task-uuid>",
    "primary_entity_id":"<rain-uuid>",
    "contribution_type":"knowledge",
    "description":"R exercises for beginners",
    "evidence":{"url":"https://example.com/r-exercises"},
    "participants":[{"entity_id":"<rain-uuid>","role":"creator","weight":1.0}]
  }'

# 4. Auto-verify (multi-witness + optional auto-finalize)
curl -X POST http://localhost:8000/api/v1/contributions/<contrib-id>/auto-verify

# 5. Finalize (optional manual — legacy /approve alias)
curl -X POST http://localhost:8000/api/v1/contributions/<contrib-id>/finalize \
  -H "Content-Type: application/json" \
  -d '{"reviewer_id":"<finalizer-entity-uuid>","feedback":"Approved"}'
```

---

## 8. Invariants (Must Hold)

1. Every `approved` contribution has traceable finalization (`finalizer_entity_id`, `policy_id`, `decision_id` in ledger).
2. Every `approved` contribution has at least one witness verification record (production).
3. `ledger_records` are append-only; no updates or deletes.
4. `cp_balance` and `ai_credits` change only via `credit_transactions`.
5. Non-human entities may receive AI Credits when `entity_equal.enabled` in `pocp_rewards.yaml` (Agent/Skill executors).
6. **Any Entity type** may finalize when instance policy allows (entity-equal; no human gate).
7. AI Credits are non-transferable in V0.1.
8. Daily CP / AI Credits issuance capped by `issuance_budget` in `pocp_rewards.yaml` (Bitcoin-style discipline).

---

## 9. Anti-Abuse (V0.1 Minimum)

| Control | Implementation |
|---------|----------------|
| Starter credits cap | Fixed grant on human registration |
| No self-approval | Removed — entity-equal policy; anti-sybil via witness diversity |
| Global issuance budget | `issuance_budget` in `pocp_rewards.yaml` + `GET /issuance/budget` |
| Evidence required | `evidence` JSON non-empty on submit |
| Appeal | Rejected contributions can re-submit (new event) |

---

## 10. Implementation Map

| Spec section | Code location |
|--------------|---------------|
| Entity model | `backend/models/entity.py` |
| Task model | `backend/models/task.py` |
| Contribution | `backend/models/contribution.py` |
| Wallet / credits | `backend/models/wallet.py` |
| Ledger | `backend/models/ledger.py` |
| API routes | `backend/routers/api.py` |
| Verify + approve logic | `backend/services/contribution.py` |
| Rights rules + conversion | `backend/services/rights_conversion.py`, `config/pocp_rewards.yaml` |
| Capability receipts | `backend/services/capability_receipt.py` |
| Finalization policy | `backend/services/finalization.py`, `config/finalization_policy.yaml` |
| Graph builder | `backend/services/graph.py` |
| Frontend shell | `frontend/src/` |

---

## 11. MVP Checklist

- [x] Entity registry (Human, Agent, Skill, Organization)
- [x] Task CRUD (create + list)
- [x] Contribution submission with participants
- [x] Auto-verify + entity-equal finalize (rewards)
- [x] Finalize endpoint (+ legacy `/approve` alias)
- [x] Wallet + CP + AI Credits
- [x] Registration grant (100 AI Credits for new humans)
- [x] Self-approval blocked
- [x] Ledger records
- [x] Reputation scores
- [x] Contribution graph API
- [x] Invocation chain (Human → Agent → Skill → LLM)
- [x] R language study demo seed
- [x] Frontend dashboard + submit workflow + graph view
- [ ] User authentication (GitHub OAuth)
- [ ] Real LLM verifier integration
- [ ] AI Chat consuming credits
- [ ] Rate limits + anti-abuse

---

## 12. Current Implementation Focus

The current implementation focus is **Sprint Alpha**:

- real identity entry;
- AI Credits wallet;
- AI Chat with Credits burn;
- contribution submission;
- AI advisory verification;
- human final review;
- CP and AI Credits issuance;
- ledger and contribution graph;
- minimal anti-abuse.

Genesis entities **Lumen-0** (witness) and **DeSui** (validator) participate in advisory verification; humans retain final approval.

---

## 13. Versioning

| Version | Status | Notes |
|---------|--------|-------|
| v0.1 | **Current** | Genesis package; single-loop MVP |
| v0.2 | Planned | Auth, real AI verifier, credit spend |
| v1.0 | Future | Pilot-hardened; public deployment |

Changes to this spec require a PR with rationale. Constitutional changes (entity rights model, AI final authority) require maintainer consensus.

---

*PoCP Protocol Spec · V0.1 · Genesis*
