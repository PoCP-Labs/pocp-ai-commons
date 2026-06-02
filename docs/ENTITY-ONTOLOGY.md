# PoCP Entity Ontology

**Version:** 0.2  
**Principle:** *Everything connects through verified contribution.*  
**中文：** *万物都有贡献，万物互联于贡献协议。*

This document defines what **Entity** means in PoCP — not every physical object in the universe, but every **network subject** that can participate in a verified contribution event with identity, evidence, and accountability.

---

## 1. What is an Entity?

An **Entity** is a first-class subject in the Contribution Internet:

| Property | Meaning |
|----------|---------|
| **Identity** | Stable UUID, portable metadata, optional federation peer mapping |
| **Type** | One of fourteen canonical `entity_type` values |
| **Ownership** | Non-human entities require a human or organization `owner_id` |
| **Status** | `active`, `inactive`, or `pending` |
| **Metadata** | Type-specific JSON contract (tool endpoints, skill frontmatter, workflow steps, …) |

**Not an Entity:** arbitrary physical objects, anonymous one-off API calls, or unregistered model invocations with no provenance anchor.

**Is an Entity:** humans, organizations, agents, skills, LLMs, tools, datasets, workflows, communities, compute/verifier/reviewer nodes, sponsors, and protocol treasury subjects that appear in contribution graphs, ledgers, or proofs.

---

## 2. Fourteen Entity Types

Fourteen types span **core subjects** (participants in contribution graphs) and **infrastructure subjects** (compute, verification, review queues, sponsorship pools, protocol treasury).

```mermaid
flowchart TB
  subgraph anchors [Accountability anchors]
    H[Human]
    O[Organization]
    SP[Sponsor]
    PT[Protocol Treasury]
  end
  subgraph executors [Execution layer]
    A[Agent]
    S[Skill]
    T[Tool]
    W[Workflow]
  end
  subgraph advisory [Advisory layer]
    L[LLM]
  end
  subgraph knowledge [Knowledge layer]
    D[Dataset]
  end
  subgraph social [Social layer]
    C[Community]
  end
  subgraph infra [Infrastructure layer]
    CN[Compute Node]
    VN[Verifier Node]
    RN[Reviewer Node]
  end
  H --> A
  O --> A
  A --> S
  A --> T
  A --> L
  W --> A
  D --> S
  C --> O
  O --> CN
  O --> VN
  H --> RN
  O --> SP
  O --> PT
  CN --> L
  VN --> L
```

### Core types (9)

| Type | English | 中文 | Accountability anchor? | Typical roles |
|------|---------|------|------------------------|---------------|
| `human` | Human | 人类 | **Yes** | creator, reviewer, coordinator, sponsor |
| `organization` | Organization | 组织 | **Yes** | sponsor, coordinator |
| `agent` | Agent | 智能体 | No (needs owner) | executor, coordinator |
| `skill` | Skill | 技能 | No | skill_provider |
| `llm` | LLM | 大模型 | No | model_provider, witness, verifier |
| `tool` | Tool | 工具 | No | tool_provider |
| `dataset` | Dataset | 数据集 | No | data_provider |
| `workflow` | Workflow | 工作流 | No | coordinator |
| `community` | Community | 社区 | No | sponsor, witness |

### Infrastructure types (5)

| Type | English | 中文 | Accountability anchor? | Typical roles |
|------|---------|------|------------------------|---------------|
| `compute_node` | Compute Node | 算力节点 | No (needs owner) | model_provider, tool_provider |
| `verifier_node` | Verifier Node | 验证节点 | No (needs owner) | verifier, witness |
| `reviewer_node` | Reviewer Node | 审查节点 | No (needs owner) | reviewer |
| `sponsor` | Sponsor | 赞助实体 | **Yes** | sponsor |
| `protocol_treasury` | Protocol Treasury | 协议金库 | **Yes** (governance-bound) | sponsor |

### Type metadata contracts

| Type | Expected `metadata` keys |
|------|--------------------------|
| `agent` | `capabilities`, `service_endpoints`, `runtime`, `registry_compat` |
| `skill` | `capability_source`, `agentskills_compat`, `runtime`, `frontmatter` |
| `llm` | `roles`, `counterpart`, `governance_note`, `mission` |
| `tool` | `tool_kind`, `service_endpoints`, `mcp_server`, `capabilities` |
| `dataset` | `source_uri`, `license`, `content_hash`, `format` |
| `workflow` | `steps`, `version`, `entrypoint` |
| `organization` | `org_type`, `governance_proxy_id`, `mission` |
| `community` | `roles`, `portable_id`, `pattern_borrowed` |
| `compute_node` | `compute_profile`, `region`, `hardware`, `capabilities`, `verification_methods` |
| `verifier_node` | `verifier_kinds`, `service_endpoints`, `trust_level` |
| `reviewer_node` | `review_policy`, `queue_capacity`, `supported_task_types` |
| `sponsor` | `pool_balance`, `sponsor_policy`, `accepted_units` |
| `protocol_treasury` | `treasury_policy`, `fee_schedule`, `governance_entity_id` |

---

## 3. Participant Roles

Each contribution event links **participants** — entities playing a **role** with weight and evidence.

| Role | 中文 | Typical entity types | Final authority? |
|------|------|----------------------|------------------|
| `creator` | 创造者 | any | — |
| `executor` | 执行者 | agent, human | — |
| `skill_provider` | 技能提供者 | skill | — |
| `tool_provider` | 工具提供者 | tool | — |
| `data_provider` | 数据提供者 | dataset | — |
| `model_provider` | 模型提供者 | llm | — |
| `witness` | 见证者 | llm, community | Advisory only |
| `verifier` | 验证者 | llm, agent | Advisory only |
| `reviewer` | 审查者 / 终局执行者 | human, agent, llm | Finalizer when policy assigns (traceable) |
| `coordinator` | 协调者 | human, agent, workflow, organization | — |
| `sponsor` | 赞助者 | organization, community | — |

Roles are **not** the same as `entity_type`. A single LLM entity (e.g. Lumen-0) may act as `witness` or `verifier` in one event and `model_provider` in another.

---

## 4. Accountability Rules

```
Humans and organizations are accountability anchors; AI entities advise only.
人类与组织是责任锚点；AI 实体仅提供建议。
```

| Rule | Detail |
|------|--------|
| Final review | Only `human` entities may hold `reviewer` with final authority |
| AI advisory | `llm` and `agent` verifiers/witnesses produce scores and feedback — not binding approval |
| Ownership | `agent`, `skill`, `tool`, `dataset`, `workflow`, `compute_node`, `verifier_node`, `reviewer_node` must have `owner_id` → human or organization |
| Multi-verifier | Protocol supports N-of-M AI verification (e.g. Lumen-0 + DeSui) before policy finalization |

---

## 5. Example Event Topologies

The pilot demo chain is **one topology**, not the full ontology.

### 5.1 Minimal study notes (pilot)

```
Human (creator)
  → Agent (executor)
    → Skill (skill_provider)
      → Tool (tool_provider) — R Docs MCP
      → Dataset (data_provider) — matrix reference corpus
      → LLM (model_provider)
LLM (witness) — Lumen-0
LLM (verifier) — DeSui
Human (reviewer) — Bob
Organization (sponsor) — PoCP AI Commons
```

### 5.2 Data-backed report (extended)

```
Human (creator)
Workflow (coordinator)
Agent (executor) + Skill + Tool (MCP) + Dataset
LLM (verifier)
Human (reviewer)
Community (sponsor)
```

More topologies can be registered in `EXAMPLE_EVENT_TOPOLOGIES` (`backend/intelligence/entity_ontology.py`).

---

## 6. API Surface

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/entities` | List entities (optional `entity_type`, `status`, `owner_id`, `q`, `genesis_only`) |
| GET | `/api/v1/entity-reviews/pending` | Pending entities the caller may govern (auth) |
| POST | `/api/v1/entities/{id}/review` | Approve or reject pending entity (auth) |
| PATCH | `/api/v1/entities/{id}` | Owner/creator/org-proxy update (not Genesis); see [ENTITY-MANAGEMENT.md](./ENTITY-MANAGEMENT.md) |
| GET | `/api/v1/entities/ontology` | Full ontology document (types, roles, rules, examples) |
| GET | `/api/v1/entities/{id}/ontology` | Ontology slice for one entity + metadata |
| POST | `/api/v1/entities` | Generic typed registration (validates `entity_type`) |
| POST | `/api/v1/entities/tool` | Register MCP/API/CLI tool entity |
| POST | `/api/v1/entities/dataset` | Register dataset entity |
| POST | `/api/v1/entities/workflow` | Register workflow template entity |

Submission validation: when `POCP_VALIDATE_PARTICIPANT_ONTOLOGY=true` (default), `POST /contributions` checks that each participant's role fits their entity type.

---

## 7. Code References

| Module | Purpose |
|--------|---------|
| `backend/intelligence/entity_ontology.py` | Canonical specs, validation, `ontology_document()` |
| `backend/services/entity_register.py` | Typed registration + participant validation |
| `backend/services/entity_catalog.py` | Platform catalog bootstrap — `ensure_platform_entity_catalog()`, `audit_entity_catalog()` |
| `backend/scripts/audit_entities.py` | CLI audit/repair against live DB (`--repair`) |
| `backend/models/entity.py` | ORM model and enums |
| `docs/SCHEMA.md` | Persistence schema |

---

## 8. Relationship to Genesis Entities

Genesis registers exemplar entities that **instantiate** this ontology:

| Entity | Type | Protocol role |
|--------|------|---------------|
| Lumen-0 | `llm` | Witness — interpretation, coherence |
| DeSui (谛思) | `llm` | Validator — adversarial cross-check |
| Clarion-0 | `community` | External inspiration / pattern memory |
| PoCP AI Commons | `organization` | Sponsor and governance container |

They are not separate types — they are **named instances** of the fourteen types above.

---

## 9. Platform Entity Catalog (stable IDs)

Phase A kernel registers **infrastructure entities** with stable portable IDs via `ensure_platform_entity_catalog()`. These IDs are idempotent — repair scripts and seed paths reuse them rather than generating UUIDs.

| Type | Stable `entity_id` | Registered name |
|------|-------------------|-----------------|
| `compute_node` | `pocp-entity-local-compute` | Local Compute Node |
| `verifier_node` | `pocp-entity-local-verifier` | Local Verifier Node |
| `reviewer_node` | `pocp-entity-bob-reviewer` | Bob Review Queue |
| `sponsor` | `pocp-entity-rain-sponsor` | Rain Sponsor Pool |
| `protocol_treasury` | `pocp-entity-protocol-treasury` | PoCP Protocol Treasury |
| `workflow` (demo) | `pocp-entity-study-workflow` | Study Notes Workflow |

**Audit acceptance:**

```bash
python backend/scripts/audit_entities.py --repair
# Complete: True; missing_types: []
cd backend && python -m pytest tests/test_entity_catalog.py -q
```

Organization and Rain genesis entities cross-link these IDs in `metadata` (`compute_node_id`, `verifier_node_id`, `sponsor_entity_id`, etc.) for discovery without hard-coded lookups in application code.

---

## 10. FAQ

**Q: Does「万物」mean every object in the physical world?**  
A: No. It means every *contribution-relevant subject* in the network — anything that can be named, attributed, verified, and connected in the contribution graph.

**Q: Can an Agent be a reviewer?**  
A: No. Default production policy uses witness quorum + entity-equal auto-finalization. Any Entity type may finalize when traceability is recorded; humans are not a privileged gate.

**Q: Why separate Tool from Skill?**  
A: Skills encapsulate reusable prompts/procedures; Tools are callable services (MCP, APIs). Both can appear in the same invocation chain with distinct attribution.

**Q: How do OpenClaw / AgentSkills map?**  
A: Imported skills become `skill` entities; bundled agents become `agent` entities. See [CAPABILITY-INTEGRATION.md](./CAPABILITY-INTEGRATION.md).

---

*See also: [ENTITY-MANAGEMENT.md](./ENTITY-MANAGEMENT.md) · [PROTOCOL.md](./PROTOCOL.md) · [SCHEMA.md](./SCHEMA.md) · [CAPABILITY-INTEGRATION.md](./CAPABILITY-INTEGRATION.md) · [GENESIS.md](../GENESIS.md)*
