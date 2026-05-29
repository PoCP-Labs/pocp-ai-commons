# PoCP V0.1 Data Schema

## Core Tables

### `entities`

First-class intelligent subjects in the network.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | Primary key |
| entity_type | enum | `human`, `agent`, `skill`, … |
| name | string | Display name |
| description | text | Optional |
| owner_id | UUID FK → entities | Human/org owner for non-human entities |
| creator_id | UUID FK → entities | Who registered this entity |
| status | enum | `active`, `inactive`, `pending` |
| metadata | JSON | Type-specific config |
| created_at | timestamp | |
| updated_at | timestamp | |

### `skills`

Skill-specific extension of an entity.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| entity_id | UUID FK → entities | |
| version | string | e.g. `1.0.0` |
| prompt_template | text | Callable prompt/function definition |
| maintainer_id | UUID FK → entities | |

### `agents`

Agent-specific extension of an entity.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| entity_id | UUID FK → entities | |
| config | JSON | Agent configuration |
| maintainer_id | UUID FK → entities | |

### `tasks`

Contribution tasks available in the network.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| title | string | |
| description | text | |
| sponsor_id | UUID FK → entities | Organization or human sponsor |
| status | enum | `open`, `in_progress`, `completed`, `closed` |
| created_at | timestamp | |

### `contribution_events`

Multi-entity contribution records.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| task_id | UUID FK → tasks | |
| primary_entity_id | UUID FK → entities | Main contributor |
| contribution_type | string | e.g. `knowledge`, `review`, `creation` |
| description | text | |
| evidence | JSON | Artifacts, links, content |
| status | enum | `draft`, `submitted`, `ai_verified`, `approved`, `rejected` |
| created_at | timestamp | |

### `contribution_participants`

Many-to-many: entities participating in a contribution.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| contribution_id | UUID FK → contribution_events | |
| entity_id | UUID FK → entities | |
| role | enum | See roles below |
| weight | float | 0.0–1.0, sum ≈ 1.0 |
| evidence | JSON | Role-specific evidence |

**Roles:** `creator`, `executor`, `reviewer`, `verifier`, `tool_provider`, `data_provider`, `skill_provider`, `model_provider`, `coordinator`, `sponsor`

### `ai_verifier_results`

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| contribution_id | UUID FK | |
| model_provider | string | e.g. `deepseek`, `gpt-4o` |
| score | float | 0.0–1.0 |
| feedback | text | |
| passed | boolean | |
| created_at | timestamp | |

### `human_reviews`

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| contribution_id | UUID FK | |
| reviewer_id | UUID FK → entities | Must be human |
| approved | boolean | |
| feedback | text | |
| created_at | timestamp | |

### `wallets`

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| entity_id | UUID FK → entities | |
| cp_balance | float | Contribution Points |
| ai_credits | float | AI usage credits |

### `credit_transactions`

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| wallet_id | UUID FK | |
| contribution_id | UUID FK | Optional |
| amount | float | |
| credit_type | enum | `cp`, `ai_credits` |
| reason | string | |
| created_at | timestamp | |

### `reputation_scores`

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| entity_id | UUID FK → entities | |
| score | float | Cumulative reputation |
| category | string | e.g. `skill`, `agent`, `human` |
| updated_at | timestamp | |

### `ledger_records`

Immutable audit trail.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| contribution_id | UUID FK | |
| event_type | string | e.g. `contribution_approved` |
| payload | JSON | Full event snapshot |
| created_at | timestamp | |

### `invocation_traces` (V0.2)

Records Human → Agent → Skill → LLM call chains.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| initiator_id | UUID FK → entities | Human who started the chain |
| task_id | UUID FK | Optional |
| contribution_id | UUID FK | Optional |
| model_provider | string | e.g. `deepseek` |
| status | enum | `started`, `completed`, `failed` |
| created_at | timestamp | |

### `invocation_steps`

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| trace_id | UUID FK | |
| step_order | int | Sequence order |
| source_entity_id | UUID FK | |
| target_entity_id | UUID FK | |
| action | string | `uses`, `calls`, `invokes_llm` |

### `organizations` (V0.2)

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| entity_id | UUID FK → entities | |
| org_type | string | `community`, `school`, `dao`, etc. |
| governance_proxy_id | UUID FK → entities | Human proxy for governance |
| config | JSON | |

## Entity Relationship Diagram

```
entities ──┬── skills
           ├── agents
           ├── wallets
           └── reputation_scores

tasks ── contribution_events ──┬── contribution_participants ── entities
                               ├── ai_verifier_results
                               ├── human_reviews
                               ├── credit_transactions
                               └── ledger_records
```
