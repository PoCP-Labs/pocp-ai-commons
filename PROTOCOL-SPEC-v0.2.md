# PoCP Protocol Spec V0.2

**Minimal protocol specification for PoCP AI Commons implementation.**

This document is the builder-facing contract. For extended schema details see [docs/SCHEMA.md](./docs/SCHEMA.md). For conceptual protocol notes see [docs/PROTOCOL.md](./docs/PROTOCOL.md). For the foundational manifesto see the [pocp-manifesto](https://github.com/PoCP-Labs/pocp-manifesto).

---

## 1. Scope

V0.2 proves **one loop** with hardened Contribution Event semantics:

```text
Entity registers → receives starter AI Credits
  → completes task → submits contribution
  → AI advisory verify → human approve
  → CP + AI Credits issued → ledger written
```

**In scope:** Human, Agent, Skill entities; tasks; contributions; verification; wallets; reputation; ledger.

**Out of scope:** Tokens, on-chain anchoring, decentralized governance, public marketplace, unlimited free AI.

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

| Type | V0.2 | Notes |
|------|------|-------|
| `human` | ✅ | Contributor, reviewer, owner |
| `agent` | ✅ | Task assistant |
| `skill` | ✅ | Reusable capability |
| `llm` | provider | Used in verification; not full citizen |
| `tool` | reserved | |
| `dataset` | reserved | |
| `workflow` | reserved | |
| `organization` | ✅ | Community governance |
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

> **A Contribution Event is the minimal protocol object by which PoCP recognizes contribution.**
>
> It is not merely a submitted artifact, nor merely a reported action.
> It is a **responsibility-bearing claim** that identifiable entities created task-relevant value through collaboration.
>
> A valid Contribution Event must include:
>
> 1. a task or value context
> 2. a primary responsible entity
> 3. a set of attributed participants and roles
> 4. an evidence bundle sufficient for review
> 5. an AI advisory verification layer
> 6. an accountable human final review
> 7. a traceable rights-conversion outcome
> 8. a ledger memory reference
>
> Without these elements, a submission may exist as content, draft, or workflow data, but it does not yet qualify as a Contribution Event in the PoCP sense.

**中文协议定义：**

> Contribution Event 是 PoCP 承认贡献的最小协议对象。
>
> 它不是单纯的产出物，不是单纯的行为记录，也不是一次奖励申请。
> 它是一项**带责任的贡献主张**：若干可识别主体围绕真实任务，通过协作创造了与任务相关的增量价值，并愿意接受证据审查、验证判断、责任归属与权利转换。
>
> 只有同时具备任务上下文、责任主体、参与归因、证据包、AI 辅助验证、人类最终确认、权利转换结果与账本记忆引用，某项提交才构成 PoCP 意义上的 Contribution Event。
>
> 否则，它可以是内容、草稿、工作流数据或协作痕迹，但还不是正式贡献事件。

#### 2.4.1 Protocol Principles

A Contribution Event must satisfy **all eight principles** to be formally established:

| # | Principle | Protocol Rule |
|---|-----------|---------------|
| 1 | **Task Attachment** | Must be anchored to a real task, problem, or definable public value goal. No context, no Contribution Event. |
| 2 | **Claim Nature** | A Contribution Event is a verifiable claim, not an established fact. The system records "a subject claims to have created value" and initiates verification. |
| 3 | **Incremental Value** | PoCP records incremental contribution, not mere presence in a workflow chain. Participation ≠ contribution. |
| 4 | **Evidence Bundle** | Without evidence, a claim cannot enter the formal contribution ledger. Evidence must support: what happened, who participated, and why the claim is not empty. |
| 5 | **Verification Required** | A claim without verification must not convert to rights. AI may advise; it must not adjudicate. |
| 6 | **Accountability** | Every formal Contribution Event must have an accountable human final-review position. No accountable responsibility → no approved status. |
| 7 | **Rights Conversion** | When established, a Contribution Event must explain how it converts to CP, AI Credits, Reputation, or other rights. Distribution is a legal consequence, not a side effect. |
| 8 | **Ledger Memory** | A Contribution Event only becomes a protocol object after being written to Ledger Memory. Verification results without ledger writes are intermediate states, not protocol assets. |

#### 2.4.2 What Does NOT Qualify as a Contribution Event

The following are explicitly **not** Contribution Events:

| What It Is | Why It Is Not |
|------------|---------------|
| Content upload record | No claim, no verification, no accountability |
| Task completion declaration | No evidence bundle, no participant attribution |
| Platform reward application form | Not a value claim — a rights request without contribution |
| AI scoring output | Advisory only; lacks human accountability and evidence chain |
| Points issuance trigger | The consequence is not the cause |
| Workflow data or collaboration trace | May be evidence, but is not itself a claim |
| Draft or submission artifact | Lacks verification and ledger memory |

#### 2.4.3 Data Schema

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `id` | UUID | auto | |
| `task_id` | UUID | yes | Must reference a valid Task (§2.3) |
| `primary_entity_id` | UUID | yes | The primary responsible entity (accountability anchor) |
| `contribution_type` | string | yes | e.g. `code`, `review`, `knowledge`, `design`, `data` |
| `description` | text | yes | The claim: what value was created and how |
| `evidence` | JSON | yes | **Non-empty.** Links, artifacts, content hash, diffs |
| `status` | enum | yes | See §3 |
| `created_at` | datetime | auto | |

#### 2.4.4 When a Contribution Event Is Formally Established

A Contribution Event is **formally established** only when **all** of the following have occurred:

1. The claim is submitted (status: `submitted`)
2. Evidence is attached (non-empty `evidence` field)
3. AI advisory verification is recorded (status: `ai_verified`)
4. Accountable human review is completed (status: `approved`)
5. Rights conversion is executed (CP + AI Credits issued)
6. Ledger Memory is written (append-only `ledger_record`)

Until all six conditions are met, the event exists as a **submission** or **intermediate state** — not yet a formal Contribution Event.

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

V0.2 minimum: `creator`, `executor`, `skill_provider`

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
| `event_type` | string | e.g. `contribution_approved`, `registration_grant` |
| `payload` | JSON | Immutable snapshot |
| `created_at` | datetime | auto |

---

## 3. Contribution State Machine

```text
draft
  → submitted          (contributor submits; evidence required)
  → ai_verified        (AI advisory review recorded)
  → approved           (human reviewer approves; rights conversion + ledger write)
  → rejected           (human reviewer rejects; terminal, but can re-submit)

ai_verified may also → rejected
submitted may skip ai_verified only in dev mode (NOT in production)
```

**Production rule:** `approved` requires prior `ai_verified`.

**AI rule:** AI verification updates status to `ai_verified` but **never** to `approved`.

**Establishment rule:** Only `approved` contributions with a corresponding `ledger_record` are formally established Contribution Events per §2.4.4.

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

Default V0.2 values (override per task):

| Event | CP | AI Credits |
|-------|-----|------------|
| Registration grant | 0 | 100 |
| Small task approval | 10 | 50 |
| Medium task approval | 25 | 150 |
| Large task approval | 50 | 300 |

All issuances create `credit_transactions` and `ledger_records`.

---

## 6. REST API (V0.2)

Base path: `/api/v1`

### Read

| Method | Path | Description |
|--------|------|-------------|
| GET | `/entities` | List entities (supports `?entity_type=&status=&skip=&limit=`) |
| GET | `/entities/{id}` | Get entity |
| GET | `/skills` | List skills |
| GET | `/agents` | List agents |
| GET | `/tasks` | List tasks (supports `?skip=&limit=`) |
| GET | `/tasks/{id}` | Get task |
| GET | `/contributions` | List contributions (supports `?skip=&limit=`) |
| GET | `/contributions/{id}` | Get contribution |
| GET | `/wallets` | List wallets (supports `?skip=&limit=`) |
| GET | `/wallets/{entity_id}` | Get wallet for entity |
| GET | `/reputation` | List reputation scores (supports `?skip=&limit=`) |
| GET | `/ledger` | List ledger records (supports `?skip=&limit=`) |
| GET | `/graph` | Contribution graph (nodes + edges) |

### Write

| Method | Path | Description |
|--------|------|-------------|
| POST | `/entities` | Register entity (+ auto-create wallet for humans) |
| POST | `/tasks` | Create task |
| POST | `/contributions` | Submit contribution |
| POST | `/contributions/{id}/verify` | Record AI advisory review |
| POST | `/contributions/{id}/approve` | Human approve (issues rewards + writes ledger) |
| POST | `/contributions/{id}/reject` | Human reject (writes ledger, no rewards) |
| POST | `/ai/chat` | Spend AI Credits for AI capability (closes genesis loop) |
| GET | `/ai/chat/{entity_id}/history` | AI usage history |
| GET | `/ai/chat/{entity_id}/stats` | Aggregate AI usage stats |
| POST | `/auth/token` | Generate JWT token for entity |

### Health

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Service status + database connectivity |

---

## 7. Example Flow (curl)

```bash
# 1. Register human
curl -X POST http://localhost:8000/api/v1/entities \
  -H "Content-Type: application/json" \
  -d '{"entity_type":"human","name":"Alice"}'

# 2. Create task
curl -X POST http://localhost:8000/api/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{"title":"Write R tutorial","description":"Create 5 exercises","sponsor_id":"<sponsor-uuid>"}'

# 3. Submit contribution (evidence required)
curl -X POST http://localhost:8000/api/v1/contributions \
  -H "Content-Type: application/json" \
  -d '{
    "task_id":"<task-uuid>",
    "primary_entity_id":"<alice-uuid>",
    "contribution_type":"knowledge",
    "description":"R exercises for beginners",
    "evidence":{"url":"https://example.com/r-exercises","content_hash":"sha256:abc..."},
    "participants":[{"entity_id":"<alice-uuid>","role":"creator","weight":1.0}]
  }'

# 4. AI verify (advisory)
curl -X POST http://localhost:8000/api/v1/contributions/<contrib-id>/verify \
  -H "Content-Type: application/json" \
  -d '{"model_provider":"gpt-4o","score":0.88,"feedback":"Good task match and evidence"}'

# 5. Human approve
curl -X POST http://localhost:8000/api/v1/contributions/<contrib-id>/approve \
  -H "Content-Type: application/json" \
  -d '{"reviewer_id":"<reviewer-uuid>","feedback":"Approved"}'
```

---

### 2.10 AI Usage Record

Record of AI Credits spent on AI capability access.
This is how the genesis loop closes: earned credits → used capability.

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID | |
| `entity_id` | UUID | Entity that used AI |
| `model_provider` | string | e.g. `pocp-default`, `deepseek` |
| `prompt` | text | User input |
| `response` | text | AI output (or null if insufficient credits) |
| `credits_deducted` | float | Credits spent on this query |
| `status` | enum | `completed`, `insufficient`, `error` |

---

## 8. Invariants (Must Hold)

1. Every `approved` contribution has exactly one human review with `approved=true`.
2. Every `approved` contribution has at least one AI verification record (production).
3. `ledger_records` are append-only; no updates or deletes.
4. `cp_balance` and `ai_credits` change only via `credit_transactions`.
5. Non-human entities never receive AI Credits in V0.2 (reputation only).
6. Human reviewers must have `entity_type=human`.
7. AI Credits are non-transferable in V0.2.
8. Every `approved` contribution must have a corresponding `ledger_record` (formal establishment).
9. `evidence` must be non-empty on submission (Principle 4: Evidence).
10. Every AI Credits spend creates a `credit_transaction` (negative amount) and a `ledger_record`.
11. AI Credits cannot go below zero; insufficient balance returns 402.
12. Reviewer cannot be the primary contributor (accountability).

---

## 9. Anti-Abuse (V0.2 Minimum)

| Control | Implementation |
|---------|----------------|
| Starter credits cap | Fixed grant on human registration |
| No self-approval | Reviewer ≠ primary contributor |
| Rate limit | Configurable via `RATE_LIMIT` env var (default 100/min/IP) |
| Evidence required | `evidence` JSON non-empty on submit; rejected if empty |
| Appeal | Rejected contributions can re-submit (new event) |
| Request ID | Every request gets `X-Request-ID` for audit trail |
| Structured logging | All requests logged with duration, status, request_id |

---

## 10. Implementation Map

| Spec section | Code location |
|--------------|---------------|
| Entity model | `backend/models/entity.py` |
| Entity service | `backend/services/entities.py` |
| Task model | `backend/models/task.py` |
| Contribution | `backend/models/contribution.py` |
| Contribution service | `backend/services/contribution.py` |
| Auth framework | `backend/services/auth.py` |
| Wallet / credits | `backend/models/wallet.py` |
| Ledger | `backend/models/ledger.py` |
| API routes | `backend/routers/` (modular) |
| Verify + approve logic | `backend/services/contribution.py` |
| Rejection logic | `backend/services/rejection.py` |
| Graph builder | `backend/services/graph.py` |
| Migrations | `backend/alembic/` |
| Config | `backend/config.py` |
| Frontend shell | `frontend/src/` |

---

## 11. MVP Checklist

- [x] Entity registry (Human, Agent, Skill, Organization)
- [x] Entity service layer with validation
- [x] Task CRUD (create + list + get by id)
- [x] Contribution submission with participants
- [x] AI verify endpoint (advisory)
- [x] Human approve endpoint (rewards + ledger)
- [x] Human reject endpoint (ledger, no rewards)
- [x] Wallet + CP + AI Credits
- [x] Registration grant (100 AI Credits for new humans)
- [x] Self-approval blocked
- [x] Ledger records (append-only)
- [x] Reputation scores
- [x] Contribution graph API
- [x] Invocation chain (Human → Agent → Skill → LLM)
- [x] R language study demo seed
- [x] Frontend dashboard + submit workflow + graph view
- [x] Pagination on all list endpoints
- [x] Error handling middleware
- [x] Rate limiting middleware
- [x] Request ID middleware
- [x] Structured logging
- [x] Database indexes (27 indexes)
- [x] Alembic migration framework
- [x] Auth token endpoint
- [x] Auth framework (demo + JWT modes)
- [x] Centralized config management
- [x] Docker production hardening
- [x] Health check with DB connectivity
- [x] Integration tests
- [x] Unit tests
- [ ] User authentication (GitHub OAuth)
- [ ] Real LLM verifier integration
- [x] AI Chat consuming credits (genesis loop closed)
- [ ] PostgreSQL support

---

## 12. Versioning

| Version | Status | Notes |
|---------|--------|-------|
| v0.1 | Superseded | Genesis package; single-loop MVP |
| v0.2 | **Current** | Hardened Contribution Event semantics; modular architecture; auth framework |
| v0.3 | Planned | GitHub OAuth, PostgreSQL, Redis, async AI verifier |
| v1.0 | Future | Pilot-hardened; public deployment |

Changes to this spec require a PR with rationale. Constitutional changes (entity rights model, AI final authority, Contribution Event definition) require maintainer consensus.

---

*PoCP Protocol Spec · V0.2 · Hardened Contribution Event*
