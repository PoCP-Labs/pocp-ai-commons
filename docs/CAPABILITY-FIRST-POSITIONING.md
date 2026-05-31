# Capability-First Positioning

**PoCP is a verifiable market for compute and AI capabilities — outside centralized platforms.**

| 属性 | 值 |
|------|-----|
| 版本 | v0.1（2026-05-29） |
| 状态 | **Canonical product direction** |
| 协议入口 | [protocol/CHAIN-AND-NODE-PLAN-v0.1.md](./protocol/CHAIN-AND-NODE-PLAN-v0.1.md) |

---

## One sentence

> **Anyone can sell compute and publish AI capabilities; anyone can buy by the unit; every exchange is Entity-attributed, metered, and ledger-auditable.**

中文：**在中心化平台之外，让普通人也能卖算力、卖 AI 能力，按单位计量、双边结算、账本可查。**

---

## What we are / are not

| We are | We are not |
|--------|------------|
| Distributed **compute + capability** exchange on the existing Internet | A new physical network or blockchain L1 |
| Entity-attributed supply (PC, Skill, Agent, LLM, MCP tool) | Another bundled ChatGPT subscription |
| Metered invoke → receipt → BC settlement | Token-first miner marketplace |
| Optional **contribution upgrade** (CP, public graph) | “Define intelligence philosophically” on every call |

---

## Terminology (canonical)

### Public (中文)

| Term | Meaning | Example |
|------|---------|---------|
| **算力** | GPU/CPU inference, training, embeddings | 按 GPU 秒、训练 epoch 计费 |
| **能力** | Callable AI capability (Skill, Agent, LLM, tool) | 按 token、按次、按 tool call 计费 |
| **提供方** | Entity that publishes compute or capability | 有 GPU 的 PC、Skill 作者 |
| **消费方** | Entity that invokes and pays BC | 学生、开发者 |
| **交换** | One metered invoke with receipt + ledger row | 不是抽象“贡献” |

Avoid as **primary** UX copy: 智力、神经网络、三链记忆。

### Protocol (English)

| Term | Schema / code |
|------|---------------|
| **Capability** | [CAPABILITY-SCHEMA-v0.3.md](./protocol/CAPABILITY-SCHEMA-v0.3.md) |
| **Compute capability** | `gpu_inference`, `training`, `embeddings` |
| **AI capability** | `reasoning`, `coding`, `tool_call`, `agent_run`, … |
| **Exchange** | [EXCHANGE-SPINE-v0.1.md](./protocol/EXCHANGE-SPINE-v0.1.md) |
| **BC / AI Credits** | Wallet settlement units |

### `exchange_kind` (v0.4)

```text
compute     — gpu_second, training_epoch, embed_batch
capability  — llm_token, skill_invocation, agent_run, mcp_tool_call
hybrid      — Agent chain with both compute and capability steps
```

Replaces informal “intelligence” in payloads. Legacy readers may map `capability` ← `intelligence`.

---

## User-facing loop (default path)

```text
发布能力 / 挂算力  →  别人 quote  →  调用  →  receipt  →  BC 变动  →  钱包可查
```

**Contribution path** (witness, CP, public graph) is **opt-in upgrade** — not required for marketplace use.

---

## Differentiation vs centralized platforms

```text
Platform:     account → vendor GPU → opaque model → vendor-owned history
PoCP:         Entity → published capability → metered receipt → portable ledger
```

Ordinary people participate as **Providers** without becoming a cloud company.

---

## Related

- [protocol/CHAIN-AND-NODE-PLAN-v0.1.md](./protocol/CHAIN-AND-NODE-PLAN-v0.1.md) — chains + nodes (engineering)
- [protocol/CAPABILITY-SCHEMA-v0.3.md](./protocol/CAPABILITY-SCHEMA-v0.3.md)
- [COMPUTE-BALANCE-SPEC.md](./COMPUTE-BALANCE-SPEC.md)
- [NEURAL-ARCHITECTURE-v0.1.md](./protocol/NEURAL-ARCHITECTURE-v0.1.md) — internal architecture metaphor (secondary)
