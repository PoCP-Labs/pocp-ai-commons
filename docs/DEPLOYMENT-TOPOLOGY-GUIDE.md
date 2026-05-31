# 部署拓扑操作指南 — 手机 · PC · 实验室 · 联邦

**读者：** Pilot 运营者、实验室管理员、节点部署工程师  
**对应：** [NEURAL-INTERNET-MASTER-PLAN.md §13](./NEURAL-INTERNET-MASTER-PLAN.md#13-典型部署拓扑)  
**前提：** [DISTRIBUTED-COMPUTE-PRIMER.md](./DISTRIBUTED-COMPUTE-PRIMER.md) · [LOCAL-SETUP.md](./LOCAL-SETUP.md)

See also: [PILOT-NEURAL-INTERNET-HANDBOOK.md](./PILOT-NEURAL-INTERNET-HANDBOOK.md) · [COMPUTE-BALANCE-SPEC.md](./COMPUTE-BALANCE-SPEC.md) · [deploy/FEDERATION-SECOND-NODE.md](../deploy/FEDERATION-SECOND-NODE.md)

---

## 0. 拓扑选型速查

| 场景 | 手机角色 | PC / 服务器角色 | PoCP Node | 关键 API |
|------|----------|-----------------|-----------|----------|
| **个人宿舍** | Human + Skill（卖智力） | LLM Entity + Ollama（卖算力） | 学校 VPS 或本地 | register · heartbeat · jobs |
| **实验室 Org** | 可选移动端审批 | 多台 LLM provider | Org 托管 Node | mesh org_only · Pool · recycle |
| **多校区联邦** | 同上 | 各校区 GPU | Node A ↔ Node B | federation providers · import-proof |

**原则：** 算力在 provider 机器上执行；Node 只调度、记账、出 Proof，不拥有 GPU。

---

## 1. 拓扑 A — 手机 + 宿舍 PC（个人最小闭环）

### 1.1 架构图

```text
┌──────────────┐     HTTPS      ┌─────────────────────────────┐
│  手机浏览器   │ ─────────────► │  PoCP Node (api.example.com) │
│  Human Entity │                │  调度 · Wallet · Proof       │
│  Skill 触发   │                └──────────────▲────────────────┘
└──────────────┘                               │
                                               │ register + heartbeat
┌──────────────┐     LAN / 内网穿透            │
│  宿舍 PC      │ ─────────────────────────────┘
│  Ollama:11434 │
│  LLM Entity   │  ← llm_inference + witness
└──────────────┘
```

### 1.2 角色分工

| 设备 | Entity 类型 | 卖什么 | 不卖什么 |
|------|-------------|--------|----------|
| 手机 | Human | 终审、审稿、CP | 重算力推理（不推荐） |
| 手机 | Skill / Agent | 智力编排、专项流程 | 本地 GPU |
| PC | LLM | `llm_inference`, `witness` | — |

### 1.3 前置条件

- [ ] PoCP Node 已部署（见 [PUBLIC-DEPLOY.md](./PUBLIC-DEPLOY.md) 或本地 `docker compose up`）
- [ ] PC 安装 Ollama（或 vLLM OpenAI-compatible），模型已 pull（如 `qwen2.5:7b`）
- [ ] PC 能访问 Node API（公网 HTTPS 或 tailscale/frp 内网穿透）
- [ ] 手机 GitHub 登录完成，Human Entity + Wallet 已创建

**Ollama 非必须：** `endpoints.base_url` 可指向 vLLM、本地 mock adapter、或实验室 OpenAI-compatible 网关。

### 1.4 Step 1 — 手机上创建 / 绑定 Entity

1. 浏览器打开 `https://app.your-domain.com`，GitHub Login。
2. 确认 `GET /api/v1/me` 返回 `entity_id` 与 `wallet.ai_credits`。
3. （可选）导入或创建 Skill Entity — 见 [PILOT-ONBOARDING.md](./PILOT-ONBOARDING.md)。

### 1.5 Step 2 — PC 上注册算力 provider

在 PC 终端（需 Bearer token，与 Human 同一账号或 Org owner）：

```bash
API=https://api.your-domain.com
TOKEN="<access_token>"

# 1) 创建或选定 LLM Entity id（seed 或 UI 创建后复制）
LLM_ENTITY_ID="<uuid>"

# 2) 注册 ComputeProfile
curl -s -X POST "$API/api/v1/compute/entities/$LLM_ENTITY_ID/register" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "active",
    "offers": [
      { "capability": "llm_inference", "adapters": ["ollama"], "models": ["qwen2.5:7b"] },
      { "capability": "witness", "adapters": ["ollama", "mock"] }
    ],
    "endpoints": { "base_url": "http://127.0.0.1:11434" },
    "capacity": { "region": "dorm", "max_concurrent": 1 },
    "policy": {
      "visibility": "public_vouched",
      "accepts_public_jobs": true
    },
    "accountability": { "owner_entity_id": "<your-human-entity-id>" }
  }'
```

**注意：** Node 在 VPS 上时，`base_url` 必须是 **Node 能访问到的地址**（非 PC 本机 127.0.0.1，除非 Node 与 Ollama 同机）。常见做法：

| 部署 | `base_url` 示例 |
|------|-----------------|
| Node 与 Ollama 同机 | `http://127.0.0.1:11434` |
| Node 远程，PC 内网 | tailscale IP：`http://100.x.x.x:11434` |
| 实验室 frp | `https://ollama-proxy.lab.example/v1` |

### 1.6 Step 3 — 心跳保活

Ollama 进程不会自动向 PoCP 报心跳；需在 PC 上定时任务：

```bash
# 每 5 分钟（cron / systemd timer）
curl -s -X POST "$API/api/v1/compute/entities/$LLM_ENTITY_ID/heartbeat" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status": "active"}'
```

超时未 heartbeat 的 provider 会被标记 offline，调度器跳过。

### 1.7 Step 4 — 手机发起第一次消费

1. 领取或创建 Task / Contribution（绑定 `contribution_id`）。
2. 提交贡献或触发 Skill 执行 → 调度器选 PC 上的 LLM provider。
3. 验证：
   - `GET /api/v1/compute/providers` 含你的 Entity
   - Contribution Proof 含 `compute_attribution`
   - Wallet：consumer 扣 Token、provider 加 Token（见 [COMPUTE-METERING-SPEC.md](./COMPUTE-METERING-SPEC.md)）

### 1.8 Step 5 — 卖智力（手机 Skill）

Skill 路径不注册 `compute_profile`；通过 `POST /api/v1/capabilities/execute` 编排下游 LLM：

```text
Human/Agent 发起
  → Skill Entity 执行链（InvocationTrace）
  → scheduler 选 PC LLM provider
  → IntelReceipt + ComputeReceipt → settlement
```

手机只需保持登录态与 Skill 配置；算力仍由 PC provider 供给。

### 1.9 常见问题

| 现象 | 原因 | 处理 |
|------|------|------|
| 调度选不到 PC provider | heartbeat 超时 / mesh 不可见 | 检查 heartbeat cron；`policy.visibility` |
| 远程 Ollama 连接失败 | Node 访问不到 `base_url` | 改 tailscale/frp；或 Node 本地 adapter |
| 402 Insufficient credits | Wallet 余额不足 | 完成贡献验证或 sponsor 充值 |
| witness 走 mock | Ollama witness 失败 | 检查模型是否支持 witness prompt |

---

## 2. 拓扑 B — 实验室 Org + ComputePool

### 2.1 架构图

```text
                    ┌──────────────── Org Entity ────────────────┐
                    │  ComputePool (Token 水库)                   │
                    │  mesh: org_only                               │
                    └────────────▲──────────────────────────────────┘
                                 │ deposit · auto-deposit from settlement
        ┌────────────────────────┼────────────────────────┐
        │                        │                        │
   LLM-1 (GPU-A)            LLM-2 (GPU-B)           Tool (embeddings)
   compute_profile          compute_profile         compute_profile
        │                        │                        │
        └────────────────────────┴────────────────────────┘
                                 │
                    PoCP Node (lab-api.example.com)
                                 │
              Students (Human) ──┴── Agents / Skills
```

### 2.2 Org 策略要点

| 配置项 | 推荐值 | 说明 |
|--------|--------|------|
| `policy.visibility` | `org_only` | 仅 Org 成员可见 provider |
| `policy.organization_entity_id` | Org UUID | mesh 过滤键 |
| ComputePool | sponsor 预充 | 高峰 burst、低谷 precompute |
| surplus recycle | 夜间 cron | 闲置 GPU → Artifact |

### 2.3 Step 1 — 注册 Org 与多台 provider

每台 GPU 机器：

1. 创建 LLM Entity（metadata 关联 `organization_entity_id`）。
2. `POST .../register`，`policy` 设为：

```json
{
  "visibility": "org_only",
  "organization_entity_id": "<org-uuid>",
  "accepts_public_jobs": false
}
```

3. 各机独立 heartbeat 脚本。

验证 mesh 隔离：

```bash
curl -s "$API/api/v1/compute/providers?mesh_filter=true" \
  -H "Authorization: Bearer $ORG_MEMBER_TOKEN"
# 应只看到本 Org provider；外校账号不应看到
```

### 2.4 Step 2 — Sponsor 向 Pool 充值

```bash
curl -s -X POST "$API/api/v1/compute/pools/$ORG_ID/deposit" \
  -H "Authorization: Bearer $SPONSOR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"amount": 500, "reason": "semester_sponsor"}'
```

查询 Pool：

```bash
curl -s "$API/api/v1/compute/pools/$ORG_ID" -H "Authorization: Bearer $TOKEN"
```

Settlement 可配置自动回充 Pool（见 `pocp_rewards.yaml` → `compute_surplus`）。

### 2.5 Step 3 — 过剩回收（surplus recycle）

诊断：

```bash
curl -s "$API/api/v1/compute/balance/summary?organization_entity_id=$ORG_ID" \
  -H "Authorization: Bearer $TOKEN"
```

当 `recommendation` 为 `surplus_detected_run_recycle`：

```bash
curl -s -X POST "$API/api/v1/compute/surplus/recycle" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"organization_entity_id": "'"$ORG_ID"'", "max_providers": 3}'
```

产出 `ComputeArtifact`（内容寻址缓存），高峰 job 可 `cache_hit` 降负载。详见 [COMPUTE-BALANCE-SPEC.md](./COMPUTE-BALANCE-SPEC.md)。

### 2.6 Step 4 — 容量预约（可选）

课程开始前预订 GPU 窗口：

```bash
curl -s -X POST "$API/api/v1/compute/capacity/reservations" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "provider_entity_id": "<llm-entity-id>",
    "capability": "llm_inference",
    "window_start": "2026-06-01T08:00:00Z",
    "window_end": "2026-06-01T10:00:00Z",
    "slots": 2,
    "prepaid_credits": 50,
    "task_id": "<task-id>"
  }'
```

v0.2 预约为内存原型；生产 Pilot 需配合运营确认窗口。

### 2.7 运营节奏（建议）

| 频率 | 动作 |
|------|------|
| 实时 | 监控 `GET /api/v1/intelligence/compute/status` |
| 每小时 | 抽查 idle providers |
| 每日 | `balance/summary` → 按需 recycle |
| 每学期初 | Pool deposit；更新 `pocp_rewards.yaml` 费率 |

---

## 3. 拓扑 C — 多校区联邦

### 3.1 架构图

```text
  Campus A Node                          Campus B Node
  ┌─────────────────┐                    ┌─────────────────┐
  │ api-a.univ.edu  │◄── trusted ──────►│ api-b.univ.edu  │
  │ local providers │     federation     │ local providers │
  └────────▲────────┘                    └────────▲────────┘
           │                                         │
      GPU pool A                                 GPU pool B

  Student on A 贡献 verify
    → scheduler escalation
    → 本地满负载时选 B 的 federation mirror provider
    → Receipt 双方 Node 各留痕；v0.4 cross-node Token 清算
```

### 3.2 配置清单

| 文件 | 节点 A | 节点 B |
|------|--------|--------|
| `trusted_nodes.yaml` | 添加 B 的 URL + 公钥 | 添加 A |
| `compute_nodes.yaml` | 本地 adapter | 本地 adapter |
| TLS + JWT | 独立 | 独立 |

部署步骤： [deploy/FEDERATION-SECOND-NODE.md](../deploy/FEDERATION-SECOND-NODE.md) · [FEDERATION-OPERATOR-RUNBOOK.md](./FEDERATION-OPERATOR-RUNBOOK.md)

### 3.3 发现联邦 provider

```bash
curl -s "$API/api/v1/compute/providers/federation" -H "Authorization: Bearer $TOKEN"
```

缓存约 60s；mirror 列表不含自动注册 — 各校区仍须在本地 register 真实 GPU。

### 3.4 Proof 跨节点

1. Campus A 导出 Proof：`GET /api/v1/contributions/{id}/proof`
2. Campus B 导入：`POST /api/v1/federation/import-proof`
3. Pilot 验收：`pilot_metrics.py` 中 `federation_imports ≥ 1`

**v0.3 限制：** 跨节点 PoCP Token 双边清算在 v0.4；Pilot 阶段以 Proof 互认 + 运营对账为主。

### 3.5 联邦 imbalance 处理

| 信号 | 动作 |
|------|------|
| A 过剩、B 赤字 | B sponsor Pool deposit；A 夜间 recycle → Artifact 可联邦只读挂载（未来） |
| B provider 全 offline | A escalation 到本地 cloud adapter（最后档） |
| 跨节点延迟高 | 优先 org mesh；联邦作 backup tier |

---

## 4. 节点级 local adapter（补充路径）

除 Entity `compute_profile` 外，Node 自身可声明 local adapter（调度 **local-first**）：

**文件：** `backend/config/compute_nodes.yaml`

```yaml
node_id: lab-node-1
adapters:
  - name: ollama
    type: ollama
    base_url: http://127.0.0.1:11434
    models: [qwen2.5:7b]
  - name: mock
    type: mock
```

适用：Node 与 Ollama 同机、无需 per-Entity 注册的开发/demo 环境。

生产 Pilot 推荐 **Entity 级 register**，便于声誉、mesh、heartbeat  per-machine 管理。

---

## 5. 安全与合规检查表

- [ ] 公网 Node：`ENABLE_DEV_LOGIN=false`
- [ ] Provider `accountability.owner_entity_id` 指向可追责 Human/Org
- [ ] `org_only` mesh 已用外校账号验证隔离
- [ ] 不向社区承诺 Token 场外交易或财务回报（[NO-TOKEN-FIRST.md](../NO-TOKEN-FIRST.md)）
- [ ] 每次 job 绑定 `contribution_id` 或 `task_id`
- [ ] Pool deposit 有 sponsor 审批记录

---

## 6. 验证脚本

```bash
# 本地或 staging 一键 smoke
python backend/scripts/distributed_compute_demo_test.py https://api.your-domain.com

# Pilot 三层指标
python backend/scripts/pilot_metrics.py https://api.your-domain.com --json
```

---

## 附录 — 相关 API 速查

| 操作 | Method | Path |
|------|--------|------|
| 注册算力 | POST | `/api/v1/compute/entities/{id}/register` |
| 心跳 | POST | `/api/v1/compute/entities/{id}/heartbeat` |
| 列出 provider | GET | `/api/v1/compute/providers` |
| mesh 过滤 | GET | `/api/v1/compute/providers?mesh_filter=true` |
| 调度 job | POST | `/api/v1/compute/jobs` |
| 执行 job | POST | `/api/v1/compute/jobs/{id}/execute` |
| 平衡诊断 | GET | `/api/v1/compute/balance/summary` |
| 自动平衡 | POST | `/api/v1/compute/balance/auto-run` |
| 自动平衡状态 | GET | `/api/v1/compute/balance/auto-status` |
| 过剩回收 | POST | `/api/v1/compute/surplus/recycle` |
| Pool 充值 | POST | `/api/v1/compute/pools/{org_id}/deposit` |
| Skill 执行 | POST | `/api/v1/capabilities/execute` |
