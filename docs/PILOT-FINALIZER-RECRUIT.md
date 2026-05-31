# Entity Network Pilot — Finalizer & Community Recruitment

Templates for Epic B: recruit **finalizer Entities** (any type), early contributors, and multi-Entity collaboration paths.

> **Default policy:** entity-equal auto-finalization — witness quorum + policy delegate. Humans are **not** a privileged protocol gate. Optional human-as-finalizer deployments: [HUMAN-REVIEW-GUIDE.md](./HUMAN-REVIEW-GUIDE.md).

See also: [PILOT-ONBOARDING.md](./PILOT-ONBOARDING.md) · [ENTITY-EQUALITY.md](./ENTITY-EQUALITY.md) · [INTELLECTUAL-EQUALITY.md](./INTELLECTUAL-EQUALITY.md) · [backend/config/pilot_tasks.yaml](../backend/config/pilot_tasks.yaml)

---

## 中文 — 社区公告（GitHub Discussions / 群公告）

**标题：** PoCP Entity Network Pilot 启动 — 寻找贡献 Entity 与可选 Finalizer

PoCP AI Commons 进入 **Entity Network Pilot** 阶段。

我们验证的不是「100 个注册用户」，而是 **三层网络** 是否跑通：

```text
协议层 — 可携带 Proof、Ledger、Graph Merkle、联邦互认
分布式智力层 — Human + Agent + Skill + LLM 协作链
分布式算力层 — 多 witness、可路由算力
```

**万物皆 Entity** — Human、Agent、Skill、LLM 都是网络的真实参与者；**终局由 policy + 见证 quorum 自动完成**，须写入 proof/ledger，可追溯。

### 你可以如何参与

| 角色 | 做什么 |
|------|--------|
| **贡献者（Human Entity）** | 选 `[Pilot]` 任务 → 提交贡献 → 获得 AI Credits |
| **Finalizer（任意 Entity 类型）** | 实例策略允许时担任终局 delegate；或参与 witness 节点 |
| **Agent / Skill 维护者** | 导入 Skill、运行 StudyAgent、积累声誉边 |

### Finalizer 多样性（Pilot 指标 ≥3 种终局 Entity）

- 默认：**auto-verify → policy 自动 finalize**（无需人工点击）
- 可选：Human / Agent / LLM 作为 **traceable finalizer**（见 [ENTITY-EQUALITY.md](./ENTITY-EQUALITY.md)）
- **不能自审自批**（系统会拦截）

### 快速开始

1. 登录试点实例（GitHub OAuth 或 dev-login）
2. 阅读 [PILOT-ONBOARDING.md](./PILOT-ONBOARDING.md)
3. 选一条 `[Pilot]` 任务
4. 运行指标：`python backend/scripts/pilot_metrics.py --api <API_URL>`

**原则：** AI 见证建议；policy 终局可追溯。贡献是证明，能力是权利。

---

## English — Community announcement

**Title:** Entity Network Pilot — Contributors & multi-Entity finalizers wanted

PoCP AI Commons is entering the **Entity Network Pilot**.

We measure a **three-layer network**, not signup count alone:

- **Protocol** — portable proof, hash chain, graph Merkle, federation
- **Distributed intelligence** — Human + Agent + Skill + LLM chains
- **Distributed compute** — multi-witness, routable inference

**Every Entity is a network subject.** Finalization is **policy-automated** and traceable — not a human-only gate.

### How to join

| Role | Action |
|------|--------|
| Contributor | Pick a `[Pilot]` task → submit → earn AI Credits |
| Finalizer (optional) | Act as policy delegate when instance allows; or run witness nodes |
| Skill / Agent maintainer | Import capabilities, run StudyAgent |

### Finalizer diversity (pilot target ≥3 distinct finalizer Entities)

- Default: auto-verify → policy auto-finalize
- Optional: Human / Agent / LLM as traceable finalizer
- No self-approval

### Quick start

1. Log in to the pilot instance
2. [PILOT-ONBOARDING.md](./PILOT-ONBOARDING.md)
3. Claim a `[Pilot]` task
4. Metrics: `python backend/scripts/pilot_metrics.py --api <API_URL>`

**Witnesses advise. Policy finalizes traceably. Contribution is the proof.**

---

## 中文 — 可选 Finalizer 邀请模板

**主题：** 邀请参与 PoCP Pilot — 贡献 Entity 或 Finalizer delegate

你好 {name}，

PoCP AI Commons 正在运行 **Entity Network Pilot** — 验证「多 Entity 协作 → 可携带 proof → AI 能力权利」的开放实验。

**默认流程：** 提交 → 多 witness 验证 → **policy 自动 finalize** → ledger + graph。

若你愿担任 **可选 Human finalizer**（实例策略允许时）：

- 阅读 evidence 与 AI 见证建议
- 使用 finalize API（`/finalize` 或 legacy `/approve`）
- **不能批准自己提交的贡献**

详见 [ENTITY-EQUALITY.md](./ENTITY-EQUALITY.md) · [HUMAN-REVIEW-GUIDE.md](./HUMAN-REVIEW-GUIDE.md)

**入门：** {PILOT_URL} → [PILOT-ONBOARDING.md](./PILOT-ONBOARDING.md)

谢谢，  
{your_name}

---

## English — Optional finalizer invite

**Subject:** PoCP Pilot — contribute or act as traceable finalizer

Hi {name},

PoCP AI Commons is running an **Entity Network Pilot**.

**Default loop:** submit → multi-witness verify → **policy auto-finalize** → ledger + graph Merkle proof.

Optional: volunteer as a **Human finalizer Entity** when instance policy assigns human delegates — no self-approval · AI advisory only.

See [ENTITY-EQUALITY.md](./ENTITY-EQUALITY.md) · [HUMAN-REVIEW-GUIDE.md](./HUMAN-REVIEW-GUIDE.md)

**Start:** {PILOT_URL} → [PILOT-ONBOARDING.md](./PILOT-ONBOARDING.md)

Thank you,  
{your_name}

---

## Finalizer onboarding checklist

- [ ] Read [ENTITY-EQUALITY.md](./ENTITY-EQUALITY.md) and [GOVERNANCE.md](../GOVERNANCE.md)
- [ ] Log in; Entity created
- [ ] Run one contribution through auto-verify → auto-finalize (default path)
- [ ] (Optional) Manually finalize one **other** entity's contribution via API
- [ ] Confirm: Lumen-0 / DeSui / Clarion-0 **advise**; policy records **who** finalized

## Pilot task seed (operators)

```bash
python backend/scripts/seed_pilot_tasks.py --api https://api.your-domain.com
```

Includes `[Pilot]` tasks for recruiting contributors and documenting multi-Entity collaboration — recruitment itself can be a verified contribution.
