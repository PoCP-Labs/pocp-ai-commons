# Agent Studio — Self-Evolving Meta Agent Sub-Platform

**Status:** v1.0 open-core foundation  
**API:** `/api/v1/agent-studio/*`  
**UI:** Dashboard tab **Agent Studio**

Agent Studio is a dedicated sub-platform for **engineering Meta Agents** (Nexus, Forge, Vault, …). It implements a verifiable **Observe → Evaluate → Refine** loop so the system can **learn, grow, transform, and improve** without violating PoCP governance.

## Four pillars

| Pillar | Mechanism | Studio artifact |
|--------|-----------|-----------------|
| **Learn** | Record outcomes (tests, acceptance, reviews) | `agent_studio_outcomes` |
| **Grow** | Auto-propose capability elevation after pass streaks | `capability_add` proposals |
| **Transform** | Apply approved changes to `Agent.config.learning_profile` | `POST .../proposals/{id}/apply` |
| **Improve** | Failure outcomes spawn refinement proposals | `prompt_refine`, `workflow_update` |

## O.E.R. loop

```text
Mission (learn/grow/transform/improve/evolve)
    → Handoff (Agent A → Agent B / Nexus)
    → Outcome (Observe) — pass | fail | partial
    → Evaluate — process_outcome → Proposal
    → Review — Gauge / Atlas / human reviewer Entity
    → Refine — apply_proposal → learning_profile++
```

## Boundaries (non-negotiable)

1. **No autonomous git writes** — Studio updates Entity `Agent.config` and playbooks; Anchor-H / Cursor applies code.
2. **No CP/AI Credits finalization** — Meta Agents do not mint rights on live contributions.
3. **Witness separation** — Runtime agents (Lumen-0, DeSui, Clarion-0) remain protocol witnesses, not Studio coders.
4. **Open Core** — Advanced auto-routing optimizers and enterprise consoles stay in [COMMERCIAL-RESERVED-BOUNDARY.md](../../COMMERCIAL-RESERVED-BOUNDARY.md).

## Data model

- `agent_studio_missions` — evolution cycles
- `agent_studio_handoffs` — inter-agent work queue
- `agent_studio_outcomes` — learning signals
- `agent_studio_proposals` — self-improvement drafts

## API quick reference

```bash
GET  /api/v1/agent-studio/dashboard
GET  /api/v1/agent-studio/mission-plans
POST /api/v1/agent-studio/missions/from-plan/phase_a_p0   # mission + handoffs
POST /api/v1/agent-studio/missions/{id}/spawn-handoffs?plan_id=phase_a_p0
POST /api/v1/agent-studio/missions
POST /api/v1/agent-studio/missions/{id}/activate
POST /api/v1/agent-studio/handoffs
POST /api/v1/agent-studio/outcomes          # auto_evaluate=true spawns proposal
POST /api/v1/agent-studio/proposals/{id}/review
POST /api/v1/agent-studio/proposals/{id}/apply
GET  /api/v1/agent-studio/agents/{id}/learning-profile
```

### Mission plans

| plan_id | Handoffs | Focus |
|---------|----------|--------|
| `phase_a_p0` | 6 | Exchange Spine + wallet audit + Gauge gate |
| `phase_a_kernel` | 10 | Entity catalog + protocol integrity + federation gate |
| `phase_a_full` | 11 | P0 + federation import + compute + canvas + atlas + lex |
| `protocol_layer_edp` | 10 | **Protocol L2** — Entity Dialogue (Issues PL-1..PL-10) |

## Cursor integration

1. Meta Agents registered as Entities (`ensure_meta_agents` on startup).
2. Handoff blocks from `agents/prompts/_global.md` → `POST /handoffs`.
3. After pytest/acceptance → `POST /outcomes` with `result: pass|fail`.
4. Review proposals in UI or API; **Apply** bumps `evolution_version`.
5. **Apply** writes `agents/patches/{slug}-{id}.md` — merge into `agents/prompts/` manually.
6. **Graph** tab shows `studio` layer edges (`reports_to`, `orchestrates`, `handoff_to`).

### Graph studio layer

Meta Agent nodes are tagged `meta_agent: true`. Edges include Nexus `orchestrates` links, `reports_to`, org `maintains`, and recorded handoffs (`handoff_to`).

### Patch suggestions

```bash
GET /api/v1/agent-studio/proposals/{id}/patch-preview
POST /api/v1/agent-studio/proposals/{id}/apply   # also writes agents/patches/*.md
```

## Roadmap

| Phase | Studio capability |
|-------|-------------------|
| **v1 (now)** | Missions, handoffs, outcomes, proposals, dashboard |
| **v1.1** | Mission plans, CI reporter, UI handoff/outcome forms |
| **v1.2 (now)** | Handoff complete UI, patch files on apply, Graph studio layer |
| **v2** | Invocation ledger links for studio operations |
| **v3** | Federated studio peers (share learning profiles, not secrets) |

See also: [agents/META-AGENTS.md](../../agents/META-AGENTS.md) · [agents/ROSTER.md](../../agents/ROSTER.md)
