# Agent Studio — Memory Vault & Auto-Evolution

Each **Meta Agent** and the **Studio collective** (Nexus) maintain a durable **memory repository** and an **evolving capability set**.

## Layers

| Layer | Storage | Purpose |
|-------|---------|---------|
| **DB** | `agent_studio_memories` | Queryable episodic / semantic / capability / lesson entries |
| **Files** | `data/agent_studio/memory/{slug}/` | Markdown sync for humans and Cursor context |
| **Profile** | `Agent.config.learning_profile` | `evolved_capabilities`, strengths, growth_areas, `evolution_version` |
| **Spec** | `meta_agents_spec.py` | Baseline capabilities per agent |

## Automatic ingestion

When `POCP_STUDIO_AUTO_EVOLVE=true` (default):

- **Handoff completed/blocked** → episodic memory + studio lesson on success
- **Outcome recorded** → memory + `process_outcome` proposal (auto-apply coaching/growth)
- **Super-loop tick** → `run_auto_evolution_tick` compacts recent outcomes
- **Cursor handoff prompt** → last 6 memories injected as context

## API

```http
GET  /api/v1/agent-studio/memory-vault
GET  /api/v1/agent-studio/capability-matrix
GET  /api/v1/agent-studio/agents/{id}/memories
GET  /api/v1/agent-studio/agents/{id}/capabilities
POST /api/v1/agent-studio/agents/{id}/memories?title=...&content=...
POST /api/v1/agent-studio/evolution/tick
```

## Environment

| Variable | Default | Purpose |
|----------|---------|---------|
| `POCP_STUDIO_AUTO_EVOLVE` | `true` | Memory ingest + auto proposals |
| `POCP_STUDIO_AUTO_APPLY_IMPROVE` | `false` | Auto-apply failure-driven prompt_refine |

## PDCA alignment

- **Observe** — outcomes, handoffs, Cursor runs
- **Evaluate** — proposals from `process_outcome`
- **Refine** — `apply_proposal` + `evolve_capability` + memory files
- **Act** — Nexus super-loop `evolve_memory` phase
