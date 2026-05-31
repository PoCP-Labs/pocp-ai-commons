# 分布式算力层入门 — 是什么 · 怎么接入 · 怎么调度 · 怎么与智力层结合

**读者：** 协议设计者、节点运营者、Pilot 集成开发者  
**前提：** 已读 [DISTRIBUTED-LAYERS.md](./DISTRIBUTED-LAYERS.md) 三层架构；本稿回答「算力层到底在干什么」。

See also: [DISTRIBUTED-COMPUTE-RESEARCH.md](./DISTRIBUTED-COMPUTE-RESEARCH.md) · [COMPUTE-FEDERATION-SPEC.md](./COMPUTE-FEDERATION-SPEC.md) · [ENTITY-ONTOLOGY.md](./ENTITY-ONTOLOGY.md) · [DISTRIBUTED-INTELLIGENCE.md](./DISTRIBUTED-INTELLIGENCE.md)

---

## 1. 一句话定义

**PoCP 的分布式算力，不是「全网 GPU 市场」，而是：挂在 Entity 上的、可验证的、贡献绑定的推理/见证/嵌入能力。**

| 不是 | 而是 |
|------|------|
| PoCP 自建数据中心 | 各 Entity / 各节点自带 Ollama、vLLM、MCP host |
| 匿名算力池 | 每次 job 绑定 `contribution_id` 或 `task_id` |
| 黑箱 API 调用 | `ComputeReceipt` → Proof `compute_attribution` → Ledger |

反模式（必须拒绝）：

```text
用户 → PoCP 云 API → PoCP 自有 GPU →  opaque 输出
```

目标模式：

```text
Contribution / Task
  → 调度器选 Compute Provider Entity
  → 在 Rain 本机 Ollama | 实验室 vLLM | 联邦 peer 上执行
  → InvocationTrace + ComputeReceipt → Proof Packet → 声誉 / AI Credits
```

---

## 2. 算力在协议里的位置

```text
┌─────────────────────────────────────────────────────────────┐
│  协议层 — Proof · Ledger · Federation · InvocationTrace      │
└───────────────────────────▲─────────────────────────────────┘
                            │ ComputeReceipt 写入 Proof
┌───────────────────────────┴─────────────────────────────────┐
│  分布式智力层 — verify · match · execute · graph            │
│  「做什么、推荐谁、如何共识」                                  │
└───────────────────────────▲─────────────────────────────────┘
                            │ 消费算力 job
┌───────────────────────────┴─────────────────────────────────┐
│  分布式算力层 — ComputeProfile · scheduler · executor       │
│  「在哪跑、谁提供、怎么记账」                                  │
└─────────────────────────────────────────────────────────────┘
```

**记忆口诀：** 算力层**执行**，智力层**编排**，协议层**记住**。

---

## 3. 三板斧

### 3.1 接入 — 算力如何「挂」到网络上

三条入口，由简到繁：

#### A. Entity 级（主路径）— `compute_profile`

任意 Tool / LLM / Human / Org 等 Entity 可在 metadata 中声明：

```json
{
  "compute_profile": {
    "spec_version": "0.1",
    "status": "active",
    "offers": [
      { "capability": "llm_inference", "adapters": ["ollama"], "models": ["qwen2.5:7b"] },
      { "capability": "witness", "adapters": ["mock", "ollama"] }
    ],
    "endpoints": { "base_url": "http://127.0.0.1:11434" },
    "capacity": { "region": "lab", "max_concurrent": 2 },
    "accountability": { "owner_entity_id": "<human-or-org-uuid>" },
    "policy": {
      "visibility": "org_only",
      "organization_entity_id": "<org-uuid>",
      "accepts_public_jobs": false
    }
  }
}
```

| capability | 含义 |
|------------|------|
| `llm_inference` | 文本推理（Skill/Agent 执行） |
| `witness` | AI 见证 / auto-verify |
| `embeddings` | 语义嵌入 |
| `mcp_host` | 远程 MCP 工具宿主 |
| `agent_runtime` | Agent 运行时 |

**API：**

- 注册：`POST /api/v1/compute/entities/{entity_id}/register`
- 心跳：`POST /api/v1/compute/entities/{entity_id}/heartbeat`
- 发现：`GET /api/v1/compute/providers`（`?mesh_filter=true` 需登录，只看 initiator 可见 mesh）

代码：`services/compute_profile.py` · `services/compute_mesh.py`（Phase δ 组织可见性）

#### B. 节点级 — `config/compute_nodes.yaml`

声明**本 PoCP 节点**上的 local_node 角色（mock / ollama / vllm…）。调度器默认 **local-first**。

#### C. 联邦 / 校园级 — trusted peers + LAN

- **联邦：** `trusted_nodes.yaml` + `peer_compute` → peer 的 `/compute/witness` 等
- **LAN  advisory：** `GET /api/v1/compute/discovery/lan`（静态配置 + 可选 mDNS，不自动注册 provider）
- **联邦镜像：** `GET /api/v1/compute/providers/federation`（从可信 peer 拉 provider 列表，60s 缓存）

详见 [COMPUTE-FEDERATION-SPEC.md](./COMPUTE-FEDERATION-SPEC.md)。

---

### 3.2 调度 — 选谁跑，而不是怎么跑

调度与执行** deliberately 分离**：

| 阶段 | 模块 | 产出 |
|------|------|------|
| **Schedule** | `compute_scheduler.py` | `job_id` + 预选 provider + 初步 `ComputeReceipt` |
| **Execute** | `compute_executor.py` | 实际 LLM / witness 调用 + 完整 receipt + settlement |

**Schedule 输入：**

```python
ComputeJob(
    capability="llm_inference",      # 或 witness / embeddings / …
    initiator_entity_id="...",       # 发起者 Human Entity
    contribution_id="...",           # 必须绑定（API 层强制）
    task_id=None,
    constraints={"model": "qwen2.5:7b"},
)
```

**候选池与排序：**

```text
1. local_node（本机 compute_nodes.yaml）
2. Entity compute_profile（经 mesh 可见性过滤）
3. peer_node（联邦 trusted_nodes）
→ 排序：组织亲和 > 本地 > owner > compute_provider 声誉
```

**API：** `POST /api/v1/compute/jobs`（需 `contribution_id` 或 `task_id`；日/小时限额见 `anti_abuse.py`）

**Execute 两条主路径：**

| 场景 | 入口 | 函数 |
|------|------|------|
| Skill / Agent 调 LLM | `capability_execute.py` | `execute_llm_inference()` |
| 贡献 auto-verify | `engines.run_verification` | `begin_witness_job()` |

远程 Entity LLM：若 provider 的 `endpoints.base_url` 指向 OpenAI-compatible 端点，executor 会远程调用；失败则 fallback 本地 mock/OpenAI。

---

### 3.3 进 Proof — 算力如何变成可携带记忆

每次完成执行，链路如下：

```text
build_compute_receipt(...)
  → InvocationStep.metadata.compute_receipt（Skill 执行链）
  → compute_jobs 内存表（witness / 独立 job）
  → settle_compute_provider()：AI Credits + compute_provider 声誉 + ledger
  → build_compute_attribution_block()：Proof 层 compute_attribution
```

Proof Packet 中相关层：

| 层 | 内容 |
|----|------|
| `invocation_trace` | 谁调了谁、每步 metadata |
| `compute_attribution` | 聚合 receipts、verified_count、provider_entity_ids |
| `rights_and_reputation` | 含 `compute_provider` 类别声誉 |
| Ledger | `compute_provided` + `compute_settlement` 事件 |

**经济闭环（Phase γ）：**

- **Consumer：** Skill 执行时 burn AI Credits（`capability_execute`）
- **Provider：** receipt 完成时获得 AI Credits + `compute_provider` 声誉（幂等 per receipt_hash）

---

## 4. 与智力层（Capability Layer）的结合

智力层模块注册见 `intelligence/engines.py` · `GET /api/v1/intelligence/status`。

```mermaid
flowchart LR
  subgraph intel [智力层]
    M["POST /intelligence/match"]
    V[auto-verify]
    X[capability_execute]
  end
  subgraph compute [算力层]
    S[schedule_compute_job]
    E[execute_llm_inference / run_witness]
  end
  subgraph protocol [协议层]
    P[Proof compute_attribution]
  end
  M -->|recommended_compute_providers| S
  V --> S
  X --> E
  S --> E
  E --> P
```

| 智力能力 | 算力层挂接点 | 用户可见结果 |
|----------|--------------|--------------|
| **Matching** | `run_matching` 返回 `recommended_compute_providers` | IntelligencePanel「Compute」推荐块 |
| **Verification** | consensus 含 `distributed_compute.witness_job` | auto-verify 响应里可见调度 job |
| **Skill execute** | `execute_llm_inference` 写 trace + receipt | Entity 调用链 `invokes_llm` |
| **Entity profile** | 展示 `compute_profile` + `compute_provider_reputation` | Entity 详情页 |
| **Governance** | provider 列表、联邦镜像、LAN 发现 | 运营仪表盘（advisory） |

**关键设计原则：** 智力层可以**建议**用哪个 provider（match），但**调度器**做最终选择；**执行器**负责远程/fallback；**协议层**只做审计，不做推理。

---

## 5. 可见性与反滥用（Phase δ）

默认 **org_only** — 不是公开 DHT 算力市场。

| `policy.visibility` | 谁能调度 |
|---------------------|----------|
| `org_only` | 同 org、owner、accountability owner |
| `trusted_federation` | 上述 + 联邦 trusted_node |
| `public_vouched` | 上述 + 公开 job 且 provider 声誉 ≥ 阈值 |

反滥用：

- Job 必须绑定 contribution 或 task
- `DAILY_COMPUTE_JOB_LIMIT` / `HOURLY_COMPUTE_JOB_LIMIT`
- 现有 `DAILY_AI_CREDITS_BURN_LIMIT` 约束 consumer

---

## 6. 本地验收

```bash
# 1. 启动 backend（示例：本地 Postgres）
# DATABASE_URL=postgresql+psycopg://root:postgres@127.0.0.1:5432/pocp
uvicorn main:app --host 0.0.0.0 --port 8000

# 2. 跑分布式算力 demo（α+β+δ）
python backend/scripts/distributed_compute_demo_test.py http://127.0.0.1:8000
```

期望输出含：`compute providers` · `compute job scheduled` · `mesh-filtered providers` · `proof compute_attribution`。

---

## 7. 已实现 vs 仍难的

| 主题 | 状态 | 说明 |
|------|------|------|
| Entity ComputeProfile | ✅ α | 注册 / 心跳 / 发现 |
| Scheduler + Receipt | ✅ α/β | local + entity + peer |
| Proof attribution | ✅ β | `compute_attribution` 层 |
| Provider 经济 | ✅ γ | credits + reputation + ledger |
| Org mesh | ✅ δ | visibility + rate limit |
| Job 持久化 | ⏳ | 当前 in-memory `compute_jobs` |
| 跨节点 settlement | ⏳ | 联邦 mirror 偏发现 |
| SLA / 质量 quorum | ⏳ | witness 已有，算力 SLA 待产品化 |
| 开放匿名 GPU 池 | ❌ | 刻意不做 |

**真正的难点（与你直觉一致）：**

1. **定义** — 算力 = Entity 能力 + 责任，不是 API key  
2. **接入** — 注册、心跳、endpoint、组织边界要一致  
3. **调度** — 多源候选 + 信任 + 亲和 + 声誉，不能各模块各选各的  
4. **与智力层缝合** — match / verify / execute 三条线必须共享 receipt 语义  
5. **可验证与经济** — receipt 进 Proof，否则只是又一个 P2P 推理项目  

---

## 8. 与 OpenAI / DeepSeek 的关系

云 API 可以是 **某个 Entity 的 adapter**（remote OpenAI-compatible），但：

- 平台**不得**成为唯一推理入口  
- 默认路径：**本地 → 组织内 Entity → 联邦 trusted peer → 可选云 adapter**

PoCP 不拼 FLOPS，拼 **贡献绑定的可审计调度网络**。

---

## 9. 代码地图（快速索引）

|  Concern | 路径 |
|----------|------|
| Profile 注册 / 发现 | `services/compute_profile.py` |
| Mesh 可见性 | `services/compute_mesh.py` |
| 调度 | `services/compute_scheduler.py` |
| 执行 | `services/compute_executor.py` |
| Receipt | `services/compute_receipt.py` |
| Proof 聚合 | `services/compute_attribution.py` |
| 结算 / 声誉 | `services/compute_settlement.py` · `compute_reputation.py` |
| 匹配 | `services/compute_matching.py` |
| 联邦 / LAN | `compute_federation.py` · `compute_lan_discovery.py` |
| API | `routers/compute.py` |
| 智力层挂接 | `intelligence/engines.py` |
| Demo | `scripts/distributed_compute_demo_test.py` |

Phase 路线图：[DISTRIBUTED-COMPUTE-RESEARCH.md](./DISTRIBUTED-COMPUTE-RESEARCH.md) §7（α–δ 已落地）。

**支撑论证（Pilot 可引用）：** [DISTRIBUTED-COMPUTE-SUPPORT-ARGUMENT.md](./DISTRIBUTED-COMPUTE-SUPPORT-ARGUMENT.md)

**经济与计量（v0.2 草案）：** [COMPUTE-METERING-SPEC.md](./COMPUTE-METERING-SPEC.md) · [ENTITY-MARKET-SPEC.md](./ENTITY-MARKET-SPEC.md) · [DISTRIBUTED-TOKEN-RESEARCH.md](./DISTRIBUTED-TOKEN-RESEARCH.md)
