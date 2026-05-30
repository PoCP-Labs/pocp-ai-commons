# Accountability Boundary — 默认放开，最小约束

**Purpose:** PoCP **defaults to maximum automation**. Restrictions exist only where portable trust requires **traceable attribution** — not to preserve manual UI or slow agent progress.

See also: [PROTOCOL-STACK.md](./PROTOCOL-STACK.md) · [genesis/zh-CN.md](./genesis/zh-CN.md) §6

---

## One sentence

> **默认尽量放开：AI、Agent、多见证流水线、自动终局都应优先推进；协议只要求「谁/何种策略改写了权利记忆」可审计、可携带、可联邦选择接受与否。**

This is **not** “humans must approve everything.” It **is** “don’t write others’ reputation into shared memory without a trace someone can challenge.”

---

## Default stance: open automation

| Principle | Meaning |
|-----------|---------|
| **Automation first** | New capability should ship automated end-to-end; add human gates only when a deployment explicitly needs them |
| **Agents are first-class** | StudyAgent, verifier agents, reviewer agents, future autonomous runtimes — welcome in capability layer |
| **Policy over prohibition** | Prefer published **finalization policy** over hard-coded “AI cannot X” |
| **Instance sovereignty** | Each node/org chooses how open its automation is; federation = trust market, not global veto |

PoCP should **not** become a compliance cage that blocks better models, more witnesses, or agent-native workflows.

---

## Two axes (keep separate)

| Axis | PoCP stance |
|------|-------------|
| **Automation scope** | **Maximize** — matching, verify, draft, submit, auto-approve under policy, graph, governance proposals |
| **Traceability scope** | **Minimize but require** — rights-changing ledger writes record *which Entity / role / policy version* finalized the outcome |

Automation and traceability are independent: you can have **full auto-finalization** with **full audit trail**.

---

## What runs open by default (encouraged)

- Multi-model / local+remote verification; embedding match; risk scoring
- Agent runtimes with **InvocationTrace** (Human→Agent→Skill→LLM)
- Auto-verify → auto-approve pipelines when instance policy allows
- Clarion-0 (or successor agents) drafting **and executing** finalization **when delegated**
- Batch approve, committee rules, org maintainer bots bound to `reviewer_id`
- Governance automation (proposals, timelocks, parameterized policies)

**`# AI is a witness, not a ruler`** means: no **hidden, un attributable** power — not “no AI in the loop.”

---

## Minimal constraint (the only portable default)

When **portable protocol memory** changes in ways peers may import:

| Requirement | Why (minimal) |
|-------------|----------------|
| **Attribution** | Proof/ledger names finalizing Entity, role, or policy id |
| **Policy visibility** | Auto-finalization rules are versioned and readable (manifest or proof metadata) |
| **Peer choice** | Federates accept/reject imports — no forced global rule |

Everything else — human click, agent click, 3-of-5 witnesses, CP caps — is **instance policy**, not protocol dogma.

---

## Finalization patterns (all valid if traceable)

| Pattern | Notes |
|---------|-------|
| **Human reviewer** | Fine; not required as default |
| **Org / maintainer delegate** | Role-bound Entity |
| **Agent as delegate** | Valid when org charter assigns an Agent Entity as approver |
| **Witness quorum auto-approve** | e.g. N models agree + score band |
| **Governance contract / vote** | Committee, multisig, timelock |
| **Federation trust profile** | Importer trusts publisher’s policy set |

The bar is **traceability + published policy**, not **biology must click**.

---

## Clarion-0 and reviewer agents

Clarion-0’s **default in Genesis** is advisory-heavy — that is an **instance choice**, not a permanent ceiling.

An deployment may configure Clarion-0 (or a Reviewer Agent) to:

- auto-finalize low-risk bands;
- escalate only outliers;
- act as `reviewer_id` under org policy.

Protocol cares that the proof packet shows **who finalized**, not whether the finalizer was carbon or silicon.

---

## What we avoid (anti-patterns)

| Anti-pattern | Why |
|--------------|-----|
| “AI must never approve” in code or docs | Blocks progress; use policy instead |
| Silent auto-mint with no policy id | Breaks federation trust |
| Global ban on agent governance | Contradicts open capability network mission |
| Manual steps with no audit value | Ceremony without traceability |

---

## Engineering checklist

1. **Can this be automated?** → Default **yes**; ship it.
2. **Does it change reputation/rights others import?** → Add **Entity / policy version** to proof — not necessarily a human UI.
3. **Does a peer need to opt out?** → Expose policy in manifest; let federation decide.
4. **Are we adding a gate “because AI”?** → Remove unless a specific deployment asks for it.

---

## Summary

| Activity | Default |
|----------|---------|
| Verify, match, draft, agent run | ✅ Open |
| Auto-verify | ✅ Open |
| Auto-approve under published policy | ✅ Open (encouraged where safe for that instance) |
| Agent as finalizer | ✅ Open when delegated + traceable |
| Hidden / unattributed mint | ❌ Only hard no |

**North star:** PoCP is a **contribution neural network** — intelligence and compute should flow freely; the protocol’s job is **verifiable memory**, not **artificial friction**.

---

## Implementation (v0.1)

| Piece | Location |
|-------|----------|
| Policy YAML | `backend/config/finalization_policy.yaml` |
| Engine | `backend/services/finalization.py` |
| Proof field | `finalization` in contribution proof packet |
| Ledger field | `finalization` on `contribution_approved` events |
| Enable | `ENABLE_AUTO_FINALIZATION=true` |
| API | `GET /api/v1/intelligence/finalization/policy` |

After `POST …/auto-verify`, if witness quorum passes and policy is enabled, the instance auto-approves with `finalizer_entity_id` (default Clarion-0) and records policy id/version in proof.

---

## When AI exceeds human judgment

**Question:** If AI is generally smarter than humans, should PoCP still default to human final review?

**Answer:** **No** — not for quality, evidence, or routine verification. Forcing human clicks in domains where AI is strictly better is slower, costlier, and often **wronger**.

What remains human-governed is not **intelligence** but **governance**:

| Layer | After AI > human | Still needed |
|-------|------------------|--------------|
| **Judgment & execution** | Finalize via agents, witness quorums, stronger models | — |
| **Rules & constitution** | Versioned `finalization_policy` | What counts as contribution, caps, penalties |
| **Accountability & remedy** | Traceable `finalizer_entity_id` + policy in proof | Appeals, rollback, dispute resolution |
| **Federation** | Trust market of policies | No silent global black-box rule |

> **Intelligence can live in AI; traceability of rights memory and governability of rules cannot live in a black box.**

PoCP must **not** encode permanent privilege for carbon-based final review. Better models and agent finalizers should enter via **new policy versions + federated opt-in**, not protocol dogma.

Genesis may start conservatively (advisory-heavy). The portable protocol does not reserve a forever human veto on every contribution — only **traceable finalization** and **changeable rules**.

---
