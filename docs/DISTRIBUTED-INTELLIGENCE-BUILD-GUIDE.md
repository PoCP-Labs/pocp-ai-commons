# 分布式智力层构建指南 — 怎么建层 · 怎么产智力 · 怎么对外输出

**读者：** 节点运营者、Agent 集成者、Pilot Entity 负责人  
**前提：** 已读 [DISTRIBUTED-LAYERS.md](./DISTRIBUTED-LAYERS.md) · [DISTRIBUTED-INTELLIGENCE.md](./DISTRIBUTED-INTELLIGENCE.md)

See also: [DISTRIBUTED-COMPUTE-PRIMER.md](./DISTRIBUTED-COMPUTE-PRIMER.md) · [DISTRIBUTED-INTELLIGENCE-BENCHMARK.md](./DISTRIBUTED-INTELLIGENCE-BENCHMARK.md) · [protocol/CAPABILITY-SCHEMA-v0.3.md](./protocol/CAPABILITY-SCHEMA-v0.3.md) · [genesis/zh-CN.md](./genesis/zh-CN.md)

---

## 1. 一句话定义

**PoCP 的分布式智力层，不是「一个大模型 API」，而是：多 Entity 协作链上的编排、见证、匹配、图谱与算力路由 — 产出可携带的 Proof，而不是 opaque chat 回复。**

原则（当前默认）：

```text
AI witnesses. Policy finalizes. Ledger remembers.
AI 见证，策略终局，账本记忆。
```

终局由 `backend/config/finalization_policy.yaml`（`entity_equal_auto_v1`）驱动，无需人类点击批准；`POST /contributions/{id}/approve` 仍可作为可选 override。

---

## 2. 三个核心问题

### 2.1 怎么「建」分布式智力层？

智力层 **不跑 GPU**，它 **连接** 协议层与算力层：

```text
Protocol Layer          Entity · Contribution · Proof · Ledger
        ▲
Distributed Intelligence   kernel.py + engines.py + /intelligence/*
        ▲
Distributed Compute        Ollama · vLLM · peer witness · MCP
```

**最小可运行栈（单节点）：**

| 步骤 | 动作 | 验收 |
|------|------|------|
| 1 | 启动 backend + seed | `GET /api/v1/intelligence/status` 返回 `accountability_principle` |
| 2 | 注册 LLM Entity + `compute/register`（witness） | `GET /api/v1/compute/providers?capability=witness` ≥ 1 |
| 3 | 提交 Contribution + 触发 verify | 状态经 `ai_verified` → 策略 auto-finalize → `finalized` |
| 4 | 导出 Proof | `GET /api/v1/export/proof/{contribution_id}` 含 witness + finalization |

**多节点（Pilot）：**

```bash
export POCP_PILOT_MODE=true
export POCP_MIN_DISTINCT_WITNESS_NODES=2
export POCP_ALLOW_PEER_WITNESS=true
export POCP_PEER_COMPUTE_SECRET=dev-shared-secret
# BI-2: GET /api/v1/intelligence/compute/peer/trust
```

### 2.2 怎么「产」智力？

智力不是单一模型输出，而是 **六类可组合服务**：

| 类型 | 作用 | 主要入口 |
|------|------|----------|
| **Witness** | 多 LLM / peer 共识 advisory | `POST /api/v1/verification/run` · `peer:{node_id}` |
| **Orchestration** | Agent 多步执行链 | `POST /api/v1/intelligence/agents/study/run` |
| **Matching** | Skill / capability 语义匹配 | `POST /api/v1/intelligence/match` |
| **Graph** | 贡献图谱 PageRank / 审查提示 | `GET /api/v1/intelligence/graph/*` |
| **Governance** | Clarion / 策略摘要 | `GET /api/v1/intelligence/governance/summary` |
| **Compute routing** | 选 provider、调度 job | `POST /api/v1/compute/jobs` · scheduler pipeline |

**产智力的标准闭环：**

```text
Task / Message
  → ContributionEvent（含 evidence + metadata）
  → MultiVerifier / StudyAgent / Match
  → Witness quorum + policy rules
  → Finalization block + Ledger
  → Intelligence Packet / Proof export
```

### 2.3 怎么「对外输出」智力？

PoCP 不把智力锁在 UI 里；对外有 **六条输出面**：

| 输出面 | 协议 / 路径 | 适用场景 |
|--------|-------------|----------|
| **A2A Agent Card** | `GET /.well-known/agent.json` · per-Entity `/agent-card` | 外部 Agent 发现 PoCP 节点能力 |
| **A2A JSON-RPC** | `POST …/intelligence/a2a` · `SendMessage` / `GetTask` | Google A2A 兼容 Agent 互操作 |
| **Intelligence export** | `GET /api/v1/intelligence/export` | 联邦 sync · 跨节点 intelligence 镜像 |
| **Protocol status** | `GET /api/v1/intelligence/status` | 运维 / 监控 / 策略版本 |
| **Compute / peer APIs** | `/compute/*` · `/compute/peer/*` · BI-2 handshake | 算力 mesh · 远程 witness / inference |
| **Proof Packet** | `GET /api/v1/export/proof/{id}` · federation export |  portable 信任记忆 · 第三方审计 |

---

## 3. 三条 7 天实施路径

任选一条作为主路径；其余可作为并行验收项。

### 路径 A — LLM Witness Mesh（多节点见证）

**目标 Entity：** LLM + Community（peer 节点）

| 天 | 任务 | 命令 / 文件 |
|----|------|-------------|
| D1 | 本节点 Ollama/vLLM + LLM Entity 注册 | `compute/register` · `neural_network_sources.yaml` |
| D2 | 第二节点镜像 + `POCP_PEER_COMPUTE_SECRET` | `mirror_trusted_node.py` · `.env` |
| D3 | BI-2 peer trust 握手 | `GET /compute/peer/trust` · `build_peer_auth_headers` |
| D4 | `POCP_MIN_DISTINCT_WITNESS_NODES=2` 跑 verify | `peer_witness_verify_test.py` |
| D5 | 策略终局 + Clarion escalate 路径 | `finalization_policy.yaml` |
| D6 | Proof 导出含多 witness + peer node id | `export/proof` |
| D7 | Pilot metrics + 文档截图 | `pilot_metrics.py` |

**完成标准：** 同一 Contribution 上 ≥2 个 distinct witness node；auto-finalize；Proof 可联邦 import。

### 路径 B — Agent + A2A（对外 Agent 互操作）

**目标 Entity：** Agent + Skill + Human（creator）

| 天 | 任务 | 命令 / 文件 |
|----|------|-------------|
| D1 | Agent Entity + capability（`policy_delegate`） | [CAPABILITY-SCHEMA-v0.3.md](./protocol/CAPABILITY-SCHEMA-v0.3.md) |
| D2 | BI-1 Agent Card 发布 | `curl /.well-known/agent.json` |
| D3 | A2A `SendMessage` → Contribution | `POST …/entities/{agent_id}/a2a` |
| D4 | `GetTask` / `ListTasks` 状态机 | `ai_verified` → `TASK_STATE_WORKING` |
| D5 | StudyAgent 绑定 contribution | `agents/study/run` + `submit_contribution: true` |
| D6 | Match + invoke Skill | `intelligence/match` |
| D7 | 外部 Agent（或 curl）端到端 | `test_a2a_task_bridge.py` 同款 payload |

**完成标准：** 外部客户端仅通过 A2A 完成「发任务 → 见 contribution → 见 task 状态 → 拿 proof 链接」。

### 路径 C — Compute Provider Entity（卖算力 / 智力）

**目标 Entity：** LLM / Tool with `compute_profile`

| 天 | 任务 | 命令 / 文件 |
|----|------|-------------|
| D1 | ComputeProfile v0.1 写入 Entity metadata | `offers: witness \| gpu_inference` |
| D2 | `GET /compute/providers` 可发现 | scheduler registry |
| D3 | `POST /compute/jobs` 调度 | `compute_scheduler.py` |
| D4 | Receipt + bilateral settlement | `compute_settlement` · Wallet |
| D5 | Peer remote inference（可选） | `POST …/compute/inference` |
| D6 | MCP Tool Entity + invoke proof | `capabilities/import/mcp` |
| D7 | 供需平衡 operator flow | [COMPUTE-BALANCE-SPEC.md](./COMPUTE-BALANCE-SPEC.md) |

**完成标准：** Provider Entity 赚取 PoCP Token；Consumer 扣费；Receipt 进入 Proof。

---

## 4. Entity 能力登记（v0.3）

对外声明「我能提供什么智力/算力」，用 Capability 记录（不是口头配置）：

```json
{
  "capability_type": "coding",
  "unit": "skill_invocation",
  "verification_method": "policy_delegate",
  "metadata": {
    "evidence_standard": "pocp.evidence.v0.1",
    "finalization_policy": "entity_equal_auto_v1"
  }
}
```

完整字段见 [CAPABILITY-SCHEMA-v0.3.md](./protocol/CAPABILITY-SCHEMA-v0.3.md)。

---

## 5. 验收清单（Pilot）

- [ ] `GET /intelligence/status` — `auto_finalization_enabled: true`
- [ ] 至少 1 条 witness provider 或 peer witness 路径
- [ ] Contribution 从 submit → verify → finalize 无人工 approve
- [ ] Proof export 含 `witness_results` + `finalization`
- [ ] （可选）A2A SendMessage 创建 contribution
- [ ] （可选）BI-2 peer headers 通过 `validate_peer_witness_request`
- [ ] （可选）联邦 import 保留 `protocol_excerpt.intelligence`

---

## 6. 常见误区

| 误区 | 正确做法 |
|------|----------|
| 智力层 = 接一个 ChatGPT API | 智力 = 多 Entity 链 + 可验证 Contribution |
| 必须人类批准才能 finalize | 默认 policy delegate；人类 approve 为 optional |
| A2A 替代 Proof | A2A 是 **入口**；Proof 是 **记忆出口** |
| 算力层与智力层合并 | 算力执行 job；智力编排与见证 |
| Token 先行 | PoCP Token 是协议内计量；见 [NO-TOKEN-FIRST.md](../NO-TOKEN-FIRST.md) |

---

## 7. 下一步（Benchmark 路线）

| ID | 内容 | 状态 |
|----|------|------|
| BI-1 | A2A Agent Card | ✅ |
| BI-1.5 | A2A JSON-RPC task bridge | ✅ |
| BI-2 | AGT-style peer handshake | ✅ |
| BI-3 | ProvenanceKit EAA on Proof | 待做 |
| BI-4 | Proof subgraph → Knowledge Asset | 待做 |
| BI-5 | TEE attestation on ComputeReceipt | 待做 |

详见 [DISTRIBUTED-INTELLIGENCE-BENCHMARK.md](./DISTRIBUTED-INTELLIGENCE-BENCHMARK.md)。

---

## 8. 快速命令参考

```bash
# 状态
curl http://localhost:8000/api/v1/intelligence/status

# Witness providers
curl "http://localhost:8000/api/v1/compute/providers?capability=witness"

# A2A Agent Card
curl http://localhost:8000/.well-known/agent.json

# A2A SendMessage（需 Bearer）
curl -X POST "http://localhost:8000/api/v1/intelligence/entities/{agent_id}/a2a" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"SendMessage","params":{"message":{"parts":[{"kind":"text","text":"Evidence-backed change."}]}}}'

# Proof
curl "http://localhost:8000/api/v1/export/proof/{contribution_id}"
```
