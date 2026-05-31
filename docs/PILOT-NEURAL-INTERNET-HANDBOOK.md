# Pilot 神经互联网操作手册 — 注册 · 首单 · 验收

**读者：** Pilot 协调员、实验室助教、首批 provider/consumer Entity 运营者  
**对应：** [NEURAL-INTERNET-MASTER-PLAN.md §16](./NEURAL-INTERNET-MASTER-PLAN.md#16-pilot-验收标准) · [PILOT-LAUNCH-CHECKLIST.md](./PILOT-LAUNCH-CHECKLIST.md)  
**部署拓扑：** [DEPLOYMENT-TOPOLOGY-GUIDE.md](./DEPLOYMENT-TOPOLOGY-GUIDE.md)

See also: [DISTRIBUTED-COMPUTE-PRIMER.md](./DISTRIBUTED-COMPUTE-PRIMER.md) · [COMPUTE-METERING-SPEC.md](./COMPUTE-METERING-SPEC.md) · [PILOT-ONBOARDING.md](./PILOT-ONBOARDING.md)

---

## 0. 本手册解决什么

Master Plan §16 列出 8 条验收命题；本手册给出 **可执行的 Day-0 → Week-4 步骤、命令与通过标准**，使「分布式神经互联网」Pilot 可重复落地。

**Pilot 一句话目标：**

> ≥2 个 Entity 真实卖算力，≥1 条 Skill 智力链，PoCP Token 双边可对账，Proof 可导出，无中心化 GPU 依赖。

---

## 1. 角色与职责

| 角色 | 负责 | 典型人选 |
|------|------|----------|
| **Node 运营** | VPS、TLS、备份、`pocp_rewards.yaml` | 实验室 IT |
| **Sponsor** | Pool 充值、任务 CP/Credits 预算 | 课程负责人 |
| **Compute provider** | PC + Ollama/vLLM、register、heartbeat | 研究生 / 志愿者 |
| **Intel provider** | Skill/Agent 配置 | 开发者 |
| **Consumer** | Human 领任务、提交贡献 | 学生 |
| **Finalizer** | 多类型 Entity 终审 quorum | 见 [PILOT-FINALIZER-RECRUIT.md](./PILOT-FINALIZER-RECRUIT.md) |

---

## 2. Day 0 — 环境就绪

### 2.1 基础设施（运营 checklist）

完整清单见 [PILOT-LAUNCH-CHECKLIST.md Phase 0–1](./PILOT-LAUNCH-CHECKLIST.md)。最小集：

- [ ] `GET /health` → `"status": "ok"`
- [ ] HTTPS on `app.*` and `api.*`
- [ ] `ENABLE_DEV_LOGIN=false`（公网）；staging 可用 dev-login 测脚本
- [ ] `python backend/scripts/smoke_test.py https://api.staging.example.com` 通过
- [ ] Seed 或 `seed_pilot_tasks.py` 已跑

### 2.2 配置确认

| 文件 | 检查项 |
|------|--------|
| `pocp_rewards.yaml` | `compute_metering.unified_token: true` |
| `pocp_rewards.yaml` | `compute_surplus.idle_window_hours` 符合运营节奏 |
| `compute_nodes.yaml` | 至少一个 local adapter（demo） |
| `trusted_nodes.yaml` | 联邦第二节点（Epic D 时再开） |

### 2.3 基线指标快照

```bash
python backend/scripts/pilot_metrics.py https://api.your-domain.com --json > pilot_baseline.json
python backend/scripts/distributed_compute_demo_test.py https://api.your-domain.com
```

保存 `pilot_baseline.json` 供 Week-4 对比。

---

## 3. Day 1 — 第一次卖算力（Provider onboarding）

### 3.1 目标

完成 Master Plan 验收 **#1**：≥2 Entity provider 完成真实 `llm_inference`。

### 3.2 Provider A — 本机 Ollama（推荐第一台）

**设备：** 实验室 PC 或 Node 同机

1. 安装 Ollama，拉模型：`ollama pull qwen2.5:7b`
2. GitHub Login → 记录 `entity_id`（Human）与新建 LLM Entity id
3. 注册 ComputeProfile（见 [DEPLOYMENT-TOPOLOGY-GUIDE §1.5](./DEPLOYMENT-TOPOLOGY-GUIDE.md#15-step-2--pc-上注册算力-provider)）
4. 配置 heartbeat cron（每 5 分钟）
5. 验证：

```bash
curl -s "$API/api/v1/compute/providers" | jq '.provider_count'
curl -s "$API/api/v1/intelligence/compute/status" | jq .
```

**通过标准：** `provider_count ≥ 1`，status 中 `active_adapters` 含 ollama 或 mock。

### 3.3 Provider B — 第二台（peer 或第二 GPU）

复制 Provider A 步骤，使用不同 Entity id 与 `capacity.region` 标签。

可选：启用 peer witness（`ENABLE_PEER_COMPUTE`）— 见 [DISTRIBUTED-LAYERS.md](./DISTRIBUTED-LAYERS.md)。

**通过标准：** 两次独立 register；调度 job 时 `selected_provider.source` 可在两者之间变化。

### 3.4 第一次真实 inference

```bash
# 需 contribution_id（从任务/贡献列表获取）
curl -s -X POST "$API/api/v1/compute/jobs" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "capability": "llm_inference",
    "contribution_id": "<contrib-uuid>",
    "constraints": { "model": "qwen2.5:7b", "input_preview": "pilot-first-sale" }
  }' | jq '{job_id, selected_provider, receipt: .compute_receipt.integrity.receipt_hash}'
```

若 job 仅 schedule 未 execute，调用：

```bash
curl -s -X POST "$API/api/v1/compute/jobs/$JOB_ID/execute" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"context": {}}'
```

**通过标准：** 返回 `compute_receipt` 含 `receipt_hash`；`usage` 或 `pocp_tokens` 字段非空。

---

## 4. Day 2 — 第一次买算力 / 智力（Consumer onboarding）

### 4.1 目标

完成验收 **#2 #3**：Skill 执行链 + Token 双边对账。

### 4.2 Consumer 路径 A — Human 贡献 + auto-verify

1. Human 领取 Task → 创建 Contribution → 提交 evidence
2. `POST /api/v1/contributions/{id}/auto-verify`
3. 检查 witness compute job 挂上：

```bash
curl -s "$API/api/v1/contributions/$CONTRIB_ID/proof" | jq '.compute_attribution'
```

### 4.3 Consumer 路径 B — Skill 执行

```bash
curl -s -X POST "$API/api/v1/capabilities/execute" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "capability_id": "<skill-capability-id>",
    "contribution_id": "<contrib-uuid>",
    "input": { "query": "pilot skill test" }
  }' | jq '{trace_id, steps: .invocation_trace.steps | length}'
```

**通过标准：**

- `InvocationTrace` 链深度 ≥ 3（Human → Agent/Skill → LLM 理想）
- Proof 导出含 `compute_attribution`（验收 **#4**）

### 4.4 Token 对账（验收 #3）

统一 PoCP Token = Wallet `ai_credits`（1:1）。对账步骤：

```bash
# 执行前
curl -s "$API/api/v1/me" -H "Authorization: Bearer $CONSUMER_TOKEN" | jq '.wallet.ai_credits'
curl -s "$API/api/v1/me" -H "Authorization: Bearer $PROVIDER_OWNER_TOKEN" | jq '.wallet.ai_credits'

# 执行 job / Skill 后重复；consumer 减少、provider 增加

# ledger 侧（operator DB 或 API 若暴露）
# credit_transactions.reason 含 compute_settlement / capability_execute
```

| 检查 | 期望 |
|------|------|
| Consumer Δ | 负值 ≈ receipt 中 `pocp_tokens_spent` |
| Provider Δ | 正值 ≈ receipt 中 `pocp_tokens_granted` |
| 无 receipt 扣款 | 不应发生（anti-abuse） |

---

## 5. Day 3–7 — Pool · Surplus · Mesh

### 5.1 Org Pool（验收 #6）

```bash
# Sponsor 充值
curl -s -X POST "$API/api/v1/compute/pools/$ORG_ID/deposit" \
  -H "Authorization: Bearer $SPONSOR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"amount": 100, "reason": "pilot_week1"}'

# 确认 Pool 余额
curl -s "$API/api/v1/compute/pools/$ORG_ID" -H "Authorization: Bearer $TOKEN" | jq .
```

Org 内学生 job 可由 Pool 代付（settlement 自动 deposit 回 Pool，见 `compute_surplus` 配置）。

### 5.2 Surplus recycle（验收 #5）

1. 保持 provider 在线但无 job ≥ `idle_window_hours`（默认 1h，测试可调低）
2. 诊断：

```bash
curl -s "$API/api/v1/compute/balance/summary?organization_entity_id=$ORG_ID" \
  -H "Authorization: Bearer $TOKEN" | jq '{idle_providers, recommendation, artifact_count}'
```

3. 触发回收：

```bash
curl -s -X POST "$API/api/v1/compute/surplus/recycle" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"organization_entity_id": "'"$ORG_ID"'"}' | jq .
```

4. 列出 Artifact：

```bash
curl -s "$API/api/v1/compute/artifacts" -H "Authorization: Bearer $TOKEN" | jq '.count'
```

**通过标准：** `artifact_count` 增加；后续 job metadata 可出现 `cache_hit`。

### 5.3 Mesh org_only（验收 #8）

1. Org 内 provider：`visibility: org_only`
2. Org 成员：`GET .../providers?mesh_filter=true` → 可见
3. 外校账号：同一 API → **不可见** 或 `provider_count` 不含 Org GPU

记录测试账号与截图/issue 作为审计附件。

### 5.4 无中心化 GPU（验收 #7）

确认清单：

- [ ] 无 PoCP 官方 GPU 租赁文案
- [ ] `selected_provider.source` 为 `entity_profile` / `local_node` / `peer_node`，非 opaque `platform_gpu`
- [ ] 贡献绑定：无 `contribution_id` 的 job → 400

---

## 6. Week 2–4 — 规模与稳定性

### 6.1 规模目标（与 PILOT-LAUNCH-CHECKLIST 对齐）

| 层 | 目标 |
|----|------|
| 协议 | ≥30 active Entities，≥4 types，≥50 Proof |
| 智力 | ≥30 InvocationTrace，avg depth ≥3 |
| 算力 | ≥2 witness providers，live adapters |

 weekly：

```bash
python backend/scripts/pilot_metrics.py https://api.your-domain.com
python backend/scripts/pilot_metrics.py https://api.your-domain.com --strict  # CI 门禁
```

### 6.2 波动响应 playbook

| `balance/summary.recommendation` | 运营动作 |
|----------------------------------|----------|
| `surplus_detected_run_recycle` | POST `surplus/recycle` 或启用 `POCP_COMPUTE_AUTO_BALANCE=true` |
| `pool_low_sponsor_deposit` | Sponsor Pool deposit |
| `deficit_escalate_purchase` | 开 federation 或 cloud adapter（最后档） |
| `balanced` | 维持；记录 weekly 指标 |

v0.4 已提供自动 cron；Pilot 仍建议 weekly 人工抽查 `balance/auto-status`。

### 6.3 反滥用 spot check

- [ ] 无 evidence 提交 → 400
- [ ] 自批贡献 → blocked
- [ ] 日限额 429 按配置触发

---

## 7. 验收签字表（§16 完整映射）

| # | 命题 | 验证命令 / 证据 | ☐ |
|---|------|-----------------|----|
| 1 | ≥2 provider 真实 llm_inference | 两条 job receipt_hash；不同 provider entity_id | ☐ |
| 2 | ≥1 Skill 链含 Trace + Receipt | `capabilities/execute` + proof export | ☐ |
| 3 | Consumer 扣、Provider 加 Token | 前后 wallet 快照 + credit_transactions | ☐ |
| 4 | Proof 含 compute_attribution | `GET .../contributions/{id}/proof` | ☐ |
| 5 | surplus recycle → Artifact | `balance/summary` + `artifacts` count | ☐ |
| 6 | Pool deposit + precompute | pool API + recycle 日志 | ☐ |
| 7 | 无中心化 GPU | provider source 审计 | ☐ |
| 8 | mesh org_only 有效 | 内外账号对比 | ☐ |

**全部 ☐ → Pilot 神经互联网层验收通过。**

---

## 8. 故障排除

| 症状 | 排查 |
|------|------|
| job 无 provider | providers 列表、heartbeat、mesh policy |
| receipt 无 hash | job 是否 execute；adapter 超时 |
| Token 未变动 | `unified_token` 配置；settlement 日志 |
| auto-verify 无 witness | contribution status；Ollama witness adapter |
| federation 0 imports | Epic D 第二节点；import-proof 流程 |
| 测试 flaky | `db.commit()` 后查 wallet；重跑单测 `test_compute_surplus.py` |

脚本入口：

```bash
cd backend && python -m unittest discover -s tests -p "test_*.py"
```

---

## 9. 与创世纪 / 经济文档的口径

Pilot 对外表述请与 [genesis/zh-CN.md §10](./genesis/zh-CN.md) 一致：

- **PoCP Token** = 协议内使用权利（Wallet ai_credits），非场外炒作品
- **CP** = 贡献证明，不可当 Token 花
- **Entity 市场** = 双边买卖算力与智力，PoCP 不建 GPU 池

---

## 附录 A — 推荐 Pilot 周程

| 周 | 焦点 |
|----|------|
| W0 | 部署 + baseline metrics |
| W1 | 2 providers + 首次 inference + Skill 链 |
| W2 | Pool + recycle + mesh 测试 |
| W3 | 30 Entity 冲刺 + StudyAgent 循环 |
| W4 | `--strict` metrics + 签字表 + 回顾 issue |

## 附录 B — 一键命令包

```bash
export API=https://api.your-domain.com
export TOKEN="<bearer>"

python backend/scripts/distributed_compute_demo_test.py "$API"
python backend/scripts/study_agent_loop_test.py "$API"
python backend/scripts/pilot_metrics.py "$API" --json
curl -s "$API/api/v1/compute/balance/summary" -H "Authorization: Bearer $TOKEN" | jq .
```
