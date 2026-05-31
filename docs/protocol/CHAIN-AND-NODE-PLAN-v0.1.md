# Chain & Node Plan v0.1 — Capability-First

**Canonical plan** for PoCP chains and nodes under the **compute + capability** product direction.

See [CAPABILITY-FIRST-POSITIONING.md](../CAPABILITY-FIRST-POSITIONING.md) for public narrative.

| 属性 | 值 |
|------|-----|
| 协议版本 | `pocp-v0.4-capability-first` |
| 取代优先级 | Supersedes **narrative priority** of [NEURAL-ARCHITECTURE-v0.1.md](./NEURAL-ARCHITECTURE-v0.1.md); neural doc remains internal reference |

---

## 1. Design principles

1. **Two chains by default, one optional** — not three mandatory chains for every user.
2. **Entity = node subject** — Operator server hosts APIs; ordinary people are Provider/Consumer Entities.
3. **Meter before metaphysics** — gpu_second, llm_token, skill_invocation are the primary units.
4. **Attach to the Internet** — HTTPS, MCP, Ollama, federation import; no new wire protocol.
5. **Contribution is upgrade** — CP / witness / graph only when explicitly promoted.

---

## 2. Chain model (简化三链 → 2+1)

### 2.1 Primary: Exchange Chain（交换链 — 主路径）

**Purpose:** Record every metered compute/capability invoke.

```text
quote (exchange_intent)
  → invoke + receipt (exchange_executed)
  → BC debit/credit (exchange_settled)
```

| Artifact | Storage | User sees |
|----------|---------|-----------|
| CapabilityReceipt | invocation / compute receipt | 调用详情 |
| InvocationTrace | optional multi-hop | 高级 / 审计 |
| `exchange_settled` ledger row | `ledger_records` | 钱包流水 |

**Normative spec:** [EXCHANGE-SPINE-v0.1.md](./EXCHANGE-SPINE-v0.1.md)

**`exchange_kind` values:**

| Kind | capability_type examples | unit examples |
|------|-------------------------|---------------|
| `compute` | `gpu_inference`, `training`, `embeddings` | `gpu_second`, `training_epoch` |
| `capability` | `reasoning`, `coding`, `tool_call`, `agent_run` | `llm_token`, `skill_invocation`, `mcp_tool_call` |
| `hybrid` | Agent orchestrating both | mixed usage block |

### 2.2 Primary: Ledger Chain（账本链 — 权利记忆）

**Purpose:** Append-only record of BC/CP changes; wallet replay audit.

```text
exchange_settled → credit_transactions → ledger_record (hash-linked)
periodic anchor → merkle roots
```

**Invariants:** [CONSTITUTION-v0.1.md](./CONSTITUTION-v0.1.md) Art. I, II

**User sees:** Wallet balance, income/expense, export verify — not “chain” jargon.

### 2.3 Optional: Contribution Chain（贡献链 — 进阶路径）

**Purpose:** Public, CP-bearing work with witness + policy finalize.

```text
submit contribution → witness (advisory) → policy finalize → CP mint → graph edge
```

**When used:**

- Publish work to commons / course portfolio / open graph
- Earn CP beyond BC settlement
- Federation import of **approved** contributions

**When NOT used:** Routine Chat, GPU job, Skill call — stay on Exchange Chain only.

### 2.4 Retired as default UX (kept internal)

| Former “chain” | New status |
|----------------|------------|
| Signal / Structure / Memory (neural) | Engineering metaphor; maps to Exchange + Ledger + optional Graph |
| ELC | Phase 2 — Provider/Consumer **statement view**, not second truth |
| Graph Merkle | Required for contribution path; **light edge** on exchange optional Phase 3 |

---

## 3. Node model（节点 = Entity 能力面）

### 3.1 Mental model

```text
WRONG:  “PoCP 节点 = 一台服务器”
RIGHT:  “PoCP 节点 = Entity 在协议里的能力面（node facet）”
        Operator 服务器 = 托管 Instance API + Archive 的运行时
```

### 3.2 Node facet types (v0.4 canonical)

| Facet | 谁 | 卖 / 买 | 最小要求 |
|-------|-----|---------|----------|
| **Consumer** | 任何 Entity + wallet | 买算力/能力 | wallet, invoke client |
| **ComputeProvider** | Human+PC, Compute Node Entity | 卖算力 | ≥1 compute capability, receipt signer |
| **CapabilityProvider** | Human, Skill, Agent, LLM Entity | 卖能力 | ≥1 capability in manifest |
| **InstanceHost** | School, Lab, Org | 托管 API + 池子 | Archive role, health, ledger verify |
| **FederationPeer** | 第二个 InstanceHost | 互认 exchange / contribution | trusted_nodes, import API |

**Default ordinary user:** starts as **Consumer**; one click **“提供算力/发布能力”** → adds Provider facet.

### 3.3 Role simplification (vs v0.1 manifest)

| Old role (keep in code) | Capability-first grouping |
|-------------------------|---------------------------|
| Wallet | Consumer (built-in) |
| Capability, Executor | **CapabilityProvider** |
| Compute adapter | **ComputeProvider** |
| Witness, Finalizer | **Contribution path only** |
| Archive, Mirror, Audit | **InstanceHost** infrastructure |
| Trust | InstanceHost policy |

### 3.4 Node manifest (required for Providers)

`GET /api/v1/entities/{id}/node-manifest`

```json
{
  "protocol": "pocp-node-manifest-v0.2-capability-first",
  "entity_id": "human_alice",
  "facets": ["consumer", "compute_provider"],
  "capabilities": [
    {
      "capability_id": "cap_alice_gpu",
      "capability_type": "gpu_inference",
      "unit": "gpu_second",
      "exchange_kind": "compute"
    }
  ],
  "endpoints": {
    "invoke": "https://…",
    "health": "https://…/api/v1/health"
  }
}
```

Full schema evolution: [ENTITY-NODE-MANIFEST-v0.1.md](./ENTITY-NODE-MANIFEST-v0.1.md) → v0.2 in Phase 2.

### 3.5 Ordinary people → node mapping

| Person has | Entity type | Facet | Publishes |
|------------|-------------|-------|-----------|
| Gaming PC + Ollama | `human` + compute profile | ComputeProvider + CapabilityProvider | `gpu_inference`, local LLM |
| Prompt / Skill author | `human` or `skill` | CapabilityProvider | `coding`, `review`, … |
| Agent builder | `agent` | CapabilityProvider | `agent_run` |
| MCP tool pack | `tool` | CapabilityProvider | `tool_call` |
| Student / developer | `human` | Consumer | — (invoke only) |
| School IT | `organization` | InstanceHost | pool, sponsor, archive |

---

## 4. Instance topology（部署拓扑）

```text
                    Internet (HTTPS)
                           │
         ┌─────────────────┼─────────────────┐
         ▼                 ▼                 ▼
   Instance A         Instance B         Instance C
   (School)           (Lab)              (Community)
         │                 │                 │
   InstanceHost      InstanceHost       InstanceHost
   + many Entities   + many Entities    + many Entities
         │                 │                 │
         └──────── federation (L1+) ────────┘
              import exchange proofs / contributions
```

- **No new network layer** — peers are URLs in `trusted_nodes.yaml`.
- Cross-instance **capability invoke** (peer mode) uses existing federation + MCP paths.

---

## 5. End-to-end flows

### 5.1 Sell compute (ordinary PC)

```text
Human registers Entity
  → publish gpu_inference capability (manifest)
  → scheduler registers node
Consumer quotes gpu_second
  → job runs locally on Provider machine
  → ComputeReceipt signed
  → exchange_settled: consumer −BC, provider +BC
  → both wallets updated
```

### 5.2 Sell capability (Skill / LLM)

```text
Provider publishes capability (unit: skill_invocation | llm_token)
Consumer quote → invoke → InvocationTrace + receipt
  → exchange_settled (exchange_kind: capability)
```

### 5.3 Upgrade to contribution (optional)

```text
Same invoke receipt attached as evidence
  → user clicks “发布为贡献”
  → witness + policy → CP + graph
```

---

## 6. Constitution (trimmed for capability-first)

Keep hard rules:

| # | Rule |
|---|------|
| C1 | Every BC movement from invoke has `exchange_settled` + `credit_transactions.ledger_record_id` |
| C2 | Every exchange has `receipt_hash` + meter (`usage` block) |
| C3 | Provider manifests list capabilities they actually serve |
| C4 | Ledger append-only; wallet replay matches |
| C5 | Federation import declares level; no silent BC mint on mirror |

Witness quorum / CP rules apply **only** on Contribution Chain path.

Full list: [CONSTITUTION-v0.1.md](./CONSTITUTION-v0.1.md)

---

## 7. Implementation phases

### Phase 0 — Narrative & schema lock (1 week)

- [x] CAPABILITY-FIRST-POSITIONING.md
- [x] CHAIN-AND-NODE-PLAN-v0.1.md (this doc)
- [x] Rename UI copy: 算力 + 能力 (Provider tab + panel)
- [x] `exchange_kind`: `capability` in new payloads

### Phase 1 — Exchange chain wedge (2–3 weeks) **P0**

| Task | Module |
|------|--------|
| `emit_exchange_settled()` | `services/exchange_spine.py` ✅ |
| Migrate settlement | `compute_settlement.py`, `ai_chat.py` ✅ |
| FK `ledger_record_id` | migration + wallet link ✅ |
| Constitution tests C1–C2 | `tests/test_constitution.py` ✅ |

**Exit:** 100% new invokes → `exchange_settled` with `compute|capability|hybrid`.

### Phase 2 — Provider node surface (2 weeks) **P1**

| Task | Deliverable |
|------|-------------|
| Manifest v0.2 facets | `GET /entities/{id}/node-manifest` ✅ |
| Provider onboarding UI | Provider Panel + facet badges ✅ |
| Public capability directory | `GET /capabilities/directory` ✅ |
| Instance well-known | `GET /.well-known/pocp-node.json` ✅ |
| Signed receipt from Provider | receipt verification on settle (Phase 2b) ✅ optional `POCP_SIGN_COMPUTE_RECEIPTS` |

**Exit:** Ordinary user can publish one capability and receive BC on invoke.

### Phase 3 — ELC + exchange proof + federation L1 (2–3 weeks) **P1**

| Task | Deliverable |
|------|-------------|
| ELC read API | `GET /entities/{id}/local-chain` ✅ |
| Exchange proof | `GET /exchanges/{id}/proof` + `exchange_inclusion` ✅ |
| Proof verify routing | `POST /proof/verify` handles exchange proofs ✅ |
| Federation L1 import | `POST /federation/import-exchange-proof` ✅ |
| UI: ELC on entity profile | EntityDetail ✅ |

**Exit:** Export exchange proof → verify offline → import on peer (L1, no BC mint).

### Phase 4 — Instance + multi-operator pilot (ongoing) **P2**

- [x] Opt-in “publish as contribution” from receipt — `POST /exchanges/{id}/publish-contribution`
- [x] Witness role on exchange-upgrade path (default witness entity + participant)
- [x] Graph edges: `exchange` → `promoted_to` → contribution hub
- [x] Multi-operator Docker federation demo — `federation_exchange_demo_test.py` + Epic D extension

---

## 8. Code map

| Chain / facet | Primary code today | Target |
|---------------|-------------------|--------|
| Exchange | `compute_settlement.py`, `ai_chat.py`, `capability_execute.py` | `exchange_spine.py` |
| Ledger | `ledger_chain.py`, `wallet_service.py` | FK binding |
| Consumer | `routers/wallet.py`, Chat UI | quote-first UX |
| ComputeProvider | `compute_scheduler.py`, `compute_executor.py` | manifest link |
| CapabilityProvider | `capabilities` router, MCP import | directory + manifest |
| InstanceHost | `main.py`, `ledger/verify`, federation routers | well-known |
| Contribution (opt) | `contribution.py`, `finalization.py` | receipt attach entry |

---

## 9. Success metrics (capability-first)

| Metric | 90-day target |
|--------|---------------|
| Published capabilities (compute + AI) | ≥ 20 active |
| Monthly metered invokes | ≥ 1k |
| Providers earning BC | ≥ 10 Entities |
| `exchange_settled` coverage | 100% new traffic |
| Wallet replay audit pass | 100% on release |
| Federation peers with exchange import | ≥ 1 real pair |

---

## 10. Document index

| Doc | Role |
|-----|------|
| [CAPABILITY-FIRST-POSITIONING.md](../CAPABILITY-FIRST-POSITIONING.md) | Product narrative |
| **CHAIN-AND-NODE-PLAN-v0.1.md** | **This plan — chains + nodes** |
| [EXCHANGE-SPINE-v0.1.md](./EXCHANGE-SPINE-v0.1.md) | Exchange event spec |
| [CAPABILITY-SCHEMA-v0.3.md](./CAPABILITY-SCHEMA-v0.3.md) | Capability taxonomy |
| [ENTITY-NODE-MANIFEST-v0.1.md](./ENTITY-NODE-MANIFEST-v0.1.md) | Manifest (→ v0.2 facets) |
| [CONSTITUTION-v0.1.md](./CONSTITUTION-v0.1.md) | Invariants |
| [LANDING-PLAN-v0.1.md](./LANDING-PLAN-v0.1.md) | Earlier engineering phases (reference) |

**Next engineering step:** Phase 1 — implement `exchange_spine.py` + constitution tests C1–C2.
