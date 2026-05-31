# 分布式 Token 深度研究 — 算力 vs 智力 · 计量 · 「储能」类比

**Research question:** 在 PoCP 分布式 Entity 经济中，Token 如何区分算力与智力、如何分别计量、算力能否像「储能」一样被存储与调剂？

**读者：** 协议设计者、经济学建模、Pilot 架构评审  
**状态：** 研究草案 v0.1（2026-05-30）  
**关联：** [COMPUTE-METERING-SPEC.md](./COMPUTE-METERING-SPEC.md) · [ENTITY-MARKET-SPEC.md](./ENTITY-MARKET-SPEC.md) · [DISTRIBUTED-LAYERS.md](./DISTRIBUTED-LAYERS.md) · [DISTRIBUTED-COMPUTE-RESEARCH.md](./DISTRIBUTED-COMPUTE-RESEARCH.md)

---

## 1. 执行摘要

| 问题 | 结论 |
|------|------|
| **算力与智力能否用同一种 Token？** | **结算层可以统一**（AI Credits / 未来协议 Token）；**计量层必须分型**，不能只用 LLM Token 一种尺子 |
| **如何区分？** | 算力 = **执行层资源消耗**（FLOPS、GPU 秒、推理 Token）；智力 = **编排/判断/匹配/共识的服务价值**（常不含 GPU，或仅部分依赖下游算力） |
| **如何计量？** | 算力：`ComputeReceipt` + `usage`（prompt/completion/GPU-秒）；智力：`IntelReceipt` + `intel_units` + 可选等价 Token |
| **算力能像储能吗？** | **原始算力不能「存」**（推理即时消耗）；**可存储的是四类衍生物**：结算 Token、算力容量预约、计算产物（嵌入/缓存）、智力资产（Skill/图谱） |

```text
错误类比：算力 = 电 → 放进电池 → 以后用
正确类比：算力 = 发电能力 + 即时用电；可存的是「钱（Token）」「预约容量」「过去发电留下的知识」
```

---

## 2. Token 族谱 — 四种 Token，不可混用

PoCP 语境下至少存在 **四种不同物理含义** 的「Token」：

| 类型 | 英文 | 是什么 | 可转让？ | 可存储？ |
|------|------|--------|----------|----------|
| **结算 Token** | Settlement Token | Wallet 余额（Pilot = AI Credits） | Pilot 否；远期治理可选 | ✅ 天然可存 |
| **计量 Token** | Metering Token (LLM) | prompt / completion 个数 | 否（用量单位） | ❌ 用完即失 |
| **智力单位** | Intel Unit | witness 次、match 次、编排步 | 否 | ❌ 服务即时 |
| **容量单位** | Capacity Unit | GPU 并发槽、预约窗口 | 可预约 | ⏳ 时间窗内「占坑」 |

```text
                    ┌─────────────────┐
                    │  结算 Token      │  ← 真正「像钱」可存 Wallet
                    │  (AI Credits)   │
                    └────────▲────────┘
                             │ 定价表折算
        ┌────────────────────┼────────────────────┐
        │                    │                    │
┌───────┴───────┐   ┌────────┴────────┐   ┌───────┴───────┐
│ 计量 Token     │   │ Intel Unit       │   │ Capacity Unit │
│ (LLM usage)   │   │ (智力服务次数)    │   │ (算力容量预约) │
└───────────────┘   └─────────────────┘   └───────────────┘
   算力主计量           智力主计量            算力「类储能」
```

**规范引用：** 结算与折算公式见 [COMPUTE-METERING-SPEC.md](./COMPUTE-METERING-SPEC.md)；双边市场见 [ENTITY-MARKET-SPEC.md](./ENTITY-MARKET-SPEC.md)。

---

## 3. 算力 vs 智力 — 本体论区分

### 3.1 三层架构中的位置

```text
协议层     — 记住谁贡献、谁验证、谁付账（Ledger / Proof）
智力层     — 决定做什么、选谁、如何编排与共识
算力层     — 在 GPU/CPU 上实际跑模型、嵌入、见证推理
```

| 维度 | **分布式算力** | **分布式智力** |
|------|----------------|----------------|
| **定义** | 把模型/嵌入/见证推理**跑完**的能力 | 在多个 Entity 间**组织、匹配、验证、建议**的能力 |
| **典型 capability** | `llm_inference`, `embeddings`, `witness`（执行侧） | matching, orchestration, multi-verifier **quorum 编排**, graph advisory |
| **是否必须 GPU** | 通常 yes（或等效 CPU 推理） | often no；可能仅规则+图谱，或调用他人算力 |
| **PoCP 代码** | `compute_executor`, `compute_scheduler`, Ollama/vLLM | `intelligence/engines`, `capability_execute`, `finalization`, `graph_analytics` |
| **Receipt** | `ComputeReceipt` | `IntelReceipt`（v0.2）+ `InvocationTrace` 步骤 |
| **价值来源** | **稀缺计算资源**（卡、电、延迟） | **稀缺判断与编排**（声誉、领域、协作拓扑） |

### 3.2 边界案例（易混淆）

| 场景 | 归类 | 理由 |
|------|------|------|
| LLM 跑 witness 推理 | **算力**（执行）+ **智力**（见证角色） | 同一 GPU 调用；计费应 **拆分**：GPU Token → 算力；quorum 席位 → 智力 |
| Skill 调用 LLM | **智力**（编排）+ **算力**（下游 LLM） | InvocationTrace 两步；Skill 收 intel/orchestration fee；LLM Entity 收 compute fee |
| Embedding 去重 | **算力** | 纯向量计算；按 embedding Token 或向量条数 |
| PageRank 推荐 Agent | **智力** | 图谱 advisory；无 GPU 也可；按 intel_unit |
| 人类终审 | **智力**（不可自动化部分） | 不计量 GPU；可计量 review 步或 CP，不走 Token 市场 |
| 预计算缓存命中 | **算力衍生品** | 不再消耗 GPU；消费 **存储的 ComputeArtifact**（见 §6） |

### 3.3 区分原则（协议层可执行）

```text
IF  job 主要消耗 provider 的 inference/embedding/GPU 时间
    → ComputeReceipt, metering_mode = token | gpu_second

IF  job 主要产出编排、匹配、共识、建议，且可独立于单次 GPU 调用定价
    → IntelReceipt, metering_mode = intel

IF  同一 InvocationTrace 中两者皆有
    → split settlement（消费者一笔扣，多 provider 按规则分账）
```

---

## 4. 计量框架

### 4.1 算力计量 — 三层尺子

算力不能用单一「Token」完美衡量；建议 **按 capability 选主尺子**：

| Capability | 主计量 | 辅助计量 | Receipt 字段 |
|------------|--------|----------|--------------|
| `llm_inference` | **LLM Token**（prompt + completion） | latency_ms, model | `usage.prompt_tokens`, `usage.completion_tokens` |
| `embeddings` | **向量条数** 或 input Token | model, dimensions | `usage.embedding_items` |
| `witness`（GPU 推理型） | LLM Token + 固定 intel 附加 | adapter | 混合 `usage` + `intel_equivalent_tokens` |
| `mcp_host` | **调用次数** 或 wall-clock | tool name | `usage.invocation_count` |
| 未来 GPU 训练/微调 | **GPU-秒** × 型号系数 | memory_gb | `usage.gpu_seconds` |

**OpenAI 兼容路径：** 直接读 `response.usage`（见 COMPUTE-METERING-SPEC §5.1）。  
**Ollama / 本地：** 估算 + `estimated: true` + 上限 cap。

**折算到结算 Token：**

```text
consumer_credits =
  (prompt_tokens/1000) × rate_prompt[model]
  + (completion_tokens/1000) × rate_completion[model]
  + (gpu_seconds) × rate_gpu[model]    # 可选扩展
```

### 4.2 智力计量 — 三层尺子

智力服务 **往往没有** 原生 LLM Token；需要 **Intel Unit** 为主、**等价 Token** 为辅：

| 服务 | Intel Unit 定义 | 等价 Token（便于统一 UI） | 默认定价思路 |
|------|-----------------|---------------------------|--------------|
| `witness`（共识席位） | 1 quorum 成员算 1 unit | 500–2000 eq. tokens | 固定 + 声誉溢价 |
| `matching` | 1 次有效推荐 | 1000 eq. tokens | 固定 |
| `skill_orchestration` | 1 次 Skill 执行 | 下游 LLM 的 10% 或固定 | 比例 + 下限 |
| `graph_advisory` | 1 次 analytics 查询 | 500 eq. tokens | 固定 |
| `agent_planning` | 1 个 plan 步 | 按步或按链长 | 阶梯 |

**IntelReceipt 结构（草案）：**

```json
{
  "spec_version": "pocp.intel_receipt.v0.2",
  "service": "matching",
  "provider_entity_id": "uuid",
  "intel_units": 1,
  "intel_equivalent_tokens": 1000,
  "downstream_compute_receipt_hashes": ["abc..."],
  "contribution_id": "uuid"
}
```

**关键规则：** 智力 Unit **不应** 简单等于「把 witness 的 LLM Token 再算一遍」——否则 LLM provider 与 witness provider **双重收同一笔 GPU 钱**。正确做法是：

```text
LLM witness 调用：算力 Token → LLM Entity
Quorum 共识席位：Intel Unit → Witness Entity（即使内部用了 GPU，也应用 intel 表定价，或显式 split）
```

### 4.3 统一账单（用户只看到一个数）

消费者 Wallet 只扣 **一个 settlement 总数**；内部分账：

```text
Total = compute_share + intel_share + protocol_fee
compute_share = Σ ComputeReceipt 折算
intel_share     = Σ IntelReceipt 折算
```

UI 可展示明细：`852 LLM tokens + 1 match + 1 witness quorum`。

### 4.4 计量可信度

| 层级 | 信任 | PoCP 策略 |
|------|------|-----------|
| Adapter 原生 usage | 高 | 优先采用 |
| tiktoken / chars 估算 | 中 | `estimated: true`，provider 费率打折 |
| 自报 intel_units | 低 | 需 InvocationTrace 步存在 + 声誉门控 |
| GPU-秒（TEE/驱动上报） | 高（未来） | v0.4+ optional attestation |

---

## 5. 与中心化平台的计量对比

| | 中心化 API | PoCP 分布式 |
|--|------------|-------------|
| 算力计量 | 平台统一定价 Token | 各 Entity 执行 + 协议折算表 + 可选挂牌价 |
| 智力计量 |  bundled 在 API 价里 | 显式 IntelReceipt，Skill/Agent 可单独赚钱 |
| 结算 | 平台收法币 | Entity 间 settlement Token |
| 审计 | 平台账单 | Receipt → Proof |

---

## 6. 「算力能否像储能一样存储？」— 深度分析

### 6.1 能源类比

| 能源概念 | 算力类比 | 能否在 PoCP「存储」？ |
|----------|----------|------------------------|
| **电能** | 推理 FLOPS / GPU 周期 | ❌ **不能** — 推理是即时消耗，不像电池 |
| **发电能力** | Entity 的 `compute_profile` + GPU | ✅ 以 **Capacity** 形式存在（闲置算力） |
| **电网调度** | `compute_scheduler` | ✅ 实时匹配供需，不是存储 |
| **电池** | ？ | ⚠️ 见下表四类「可存物」 |
| **电费余额** | Wallet 里的 **结算 Token** | ✅ **能存** — 这才是真正的「储能」对象 |
| **存电后的产品** | 嵌入向量、缓存回答、蒸馏模型 | ✅ **ComputeArtifact** |

**结论：** 若问「算力本身能不能存」→ **不能**（热力学上推理即时发生）。  
若问「算力经济能不能像能源市场一样有余额、有容量、有库存」→ **能，但要存对对象**。

### 6.2 四类「可存储」与 PoCP 原语

```text
┌────────────────────────────────────────────────────────────────┐
│ A. 结算 Token 存储（Wallet）          — 最像「存钱」           │
│    贡献 / 卖算力 / 卖智力 → AI Credits 余额 → 随时消费          │
├────────────────────────────────────────────────────────────────┤
│ B. 算力容量预约（Capacity Reservation）— 最像「订电/订槽」       │
│    Entity 声明 max_concurrent；消费者预约时间窗 → 占坑不即时跑   │
├────────────────────────────────────────────────────────────────┤
│ C. 计算产物存储（ComputeArtifact）    — 最像「存成品电」         │
│    嵌入、KV cache、相同 input 的 hash 缓存 → 再命中时不耗 GPU    │
├────────────────────────────────────────────────────────────────┤
│ D. 智力资产存储（IntelAsset）         — 存「知识」非算力         │
│    Skill、Dataset、Contribution Graph → 降低未来智力/算力需求   │
└────────────────────────────────────────────────────────────────┘
```

#### A. 结算 Token（已实现雏形）

- `Wallet.ai_credits` — 可累积、可消费  
- **这就是用户说的「Token 储能」在协议里最正确的含义**  
- 卖算力/智力 → 入账；买 → 出账；与贡献循环闭合  

#### B. 算力容量预约（部分实现，可扩展）

已有：

```json
"capacity": { "region": "lab", "max_concurrent": 2 }
```

scheduler 在 **运行时** 选空闲 provider，但 **没有** 跨时间的「期货槽位」市场。

**v0.4 研究方向 — `ComputeCapacityToken`（容量券，非 FLOPS 本身）：**

```json
{
  "reservation": {
    "provider_entity_id": "uuid",
    "window_start": "2026-06-01T02:00:00Z",
    "window_end": "2026-06-01T04:00:00Z",
    "slots": 1,
    "capability": "llm_inference",
    "prepaid_credits": 50
  }
}
```

- 消费者 **预付 settlement Token** 锁定 provider 的并发槽  
- 窗口内未使用 → 按规则退款或部分 burn  
- 类似 AWS Reserved Instance，**不是把算力放进仓库**

#### C. 计算产物 — ComputeArtifact（研究项，未实现）

| 产物 | 存储位置 | 再次使用时 |
|------|----------|------------|
| Embedding 向量 | Dataset Entity / 本地索引 | 按 **cache hit** 计费（极低 intel + 零 gpu） |
| 相同 prompt 的 LLM 输出 | content-addressed store（input_hash） | 若 `output_hash` 匹配且 policy 允许 → 不跑 GPU |
| 量化/蒸馏小模型 | Tool Entity | 降低未来 prompt Token 数 |

**Receipt 区分：**

```json
{
  "execution_mode": "live_inference | cache_hit | artifact_replay",
  "artifact_ref": "sha256:..."
}
```

- **cache_hit**：消费者仍付少量 intel 费；**provider 不重复收 full GPU 费**（或收存储费）  
- 这是 **算力节约**，不是算力存储  

#### D. 智力资产 — IntelAsset（协议已有方向）

- Skill、verified Contribution、Graph 边 — **降低未来对 raw compute 的需求**  
- 计量上体现为：匹配到高质量 Skill → 更短 InvocationTrace → 更少 LLM Token  
- 存的是 **网络记忆**，不是 GPU 周期  

### 6.3 什么不应该做

| 错误设计 | 原因 |
|----------|------|
| 「算力 Token 钱包里存 1M FLOPS」 | FLOPS 不持久；无法验证未使用的 FLOPS |
| 允许 provider 预售未绑 receipt 的算力 | Sybil / 跑路 / 无法 Proof |
| 把 CP 当算力存储 | CP 不可 spend；语义不同 |
| 链上 NFT 代表 GPU 小时 | 脱离 receipt 审计，回到 speculation |

### 6.4 推荐术语（对外）

| 说法 | 是否采用 |
|------|----------|
| 「算力储能」 | ⚠️ 仅作比喻，需解释为 **Token 余额 + 容量预约 + 产物缓存** |
| 「结算 Token 储备」 | ✅ |
| 「算力容量预约」 | ✅ |
| 「计算产物复用」 | ✅ |

---

## 7. 统一经济模型（研究建议）

### 7.1 双轨计量、单轨结算

```text
Compute path:  job → ComputeReceipt(usage) → credits_compute
Intel path:    step → IntelReceipt(units)  → credits_intel
Settlement:    Wallet ± (credits_compute + credits_intel)
Storage:       Wallet (A) | Reservation (B) | Artifact (C) | IntelAsset (D)
```

### 7.2 与 Entity 类型的映射

| Entity | 主要卖 | 主要计量 | 可「存」什么 |
|--------|--------|----------|--------------|
| LLM / Tool | 算力 | LLM Token / GPU-秒 | 容量预约；Artifact（缓存） |
| Skill / Agent | 智力 | Intel Unit | IntelAsset（Skill 本身） |
| Human | 智力（终审） | CP / review 步 | 声誉 |
| Organization | 赞助 + 容量 | Capacity 券 | 资金池 → Token Grant |
| Dataset | 智力+算力混合 | embedding 条数 | Artifact 索引 |

### 7.3 演进路线

| 阶段 | 算力计量 | 智力计量 | 「储能」能力 |
|------|----------|----------|--------------|
| v0.1 | 固定 receipt | bundled | Wallet only |
| v0.2 | LLM Token | IntelReceipt 草案 | Wallet |
| v0.3 | + Entity 挂牌价 | split settlement | + Artifact cache hit |
| v0.4 | + GPU-秒 | quorum 分账 | + Capacity reservation |
| v1.0 | federation 清算 | cross-node intel | 可选协议 Token 转让 |

---

## 8. 开放研究问题

1. **Intel Unit 与 LLM Token 的全局汇率** — 由治理定表还是市场竞价？  
2. **cache_hit 的分账** — 原始 compute provider 是否收 storage royalty？  
3. **跨节点 Artifact** — federation 是否同步 embedding 索引？  
4. **witness 双重计费** — 同一 GPU 调用算力+智力 split 的默认比例？  
5. **GPU-秒 attestation** — TEE / 驱动级上报是否 Pilot 需要？  
6. **Capacity 二级市场** — Org 能否转卖预约槽（可能引入 speculation）？

---

## 9. 对 PoCP 创新的含义

若本研究框架成立，PoCP 相对中心化算力中心的差异不仅是「去中心化」，而是：

```text
1. 算力与智力分型计量 → 每个 Entity 按真实角色赚钱
2. 结算 Token 可储备 → 贡献网络内的「蓄水池」
3. 容量与产物可复用 → 降低重复 GPU 消耗
4. 一切绑定 Receipt → 储能、消费、出售皆可审计
```

**一句话：**

> **算力即时消耗、不可入库；Token 可储备、容量可预约、产物可复用；智力以 Unit 计量、以 Skill 与 Graph 沉淀。**

---

## 10. 参考文献（项目内）

| 文档 | 内容 |
|------|------|
| [COMPUTE-METERING-SPEC.md](./COMPUTE-METERING-SPEC.md) | Token 折算公式与 receipt 字段 |
| [ENTITY-MARKET-SPEC.md](./ENTITY-MARKET-SPEC.md) | 双边市场与 Pilot 验证 |
| [DISTRIBUTED-LAYERS.md](./DISTRIBUTED-LAYERS.md) | 三层架构 |
| [DISTRIBUTED-COMPUTE-PRIMER.md](./DISTRIBUTED-COMPUTE-PRIMER.md) | ComputeProfile 与调度 |
| [DISTRIBUTED-INTELLIGENCE.md](./DISTRIBUTED-INTELLIGENCE.md) | 智力层模块 |
| [NO-TOKEN-FIRST.md](../NO-TOKEN-FIRST.md) | 结算 Token vs 协议币 |

---

## 11. 下一步

| 优先级 | 动作 |
|--------|------|
| P0 | 评审本研究 — 确认算力/智力 split 原则 |
| P1 | 在 COMPUTE-METERING-SPEC 中增加 §GPU-秒 与 cache_hit 字段 | ✅ cache_hit in COMPUTE-CAPACITY-SPEC |
| P2 | 实现 v0.2 Token 计量 + IntelReceipt | ✅ `compute_metering.py`, `intel_receipt.py` |
| P3 | 原型 `ComputeArtifact` 查重（embedding / output hash） | ✅ `compute_artifact.py` |
| P4 | 设计 `CapacityReservation` API 草案 | ✅ COMPUTE-CAPACITY-SPEC + API |
