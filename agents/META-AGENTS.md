# Meta Agents — Entity Registry & Cursor Skills

PoCP **Meta Agents** are engineering orchestration agents registered as protocol `agent` Entities with stable IDs, Agent config, Cursor Skills, and Cursor Rules.

## Registry

| Source | Purpose |
|--------|---------|
| `backend/meta_agents_spec.py` | Canonical specs (15 agents) |
| `backend/services/meta_agent_registry.py` | DB upsert + API views |
| `agents/prompts/*.md` | Full system prompts |
| `.cursor/skills/pocp-*/SKILL.md` | Cursor Agent Skills |
| `.cursor/rules/pocp-*.mdc` | File-scoped rules |

## Entity IDs

| Agent | entity_id | Task | Cursor Skill |
|-------|-----------|------|----------------|
| Nexus-0 | `pocp-agent-nexus-0` | `pocp-nexus` | `.cursor/skills/pocp-nexus/` |
| Atlas-0 | `pocp-agent-atlas-0` | `pocp-atlas` | `.cursor/skills/pocp-atlas/` |
| Forge-0 | `pocp-agent-forge-0` | `pocp-forge` | `.cursor/skills/pocp-forge/` |
| Vault-0 | `pocp-agent-vault-0` | `pocp-vault` | `.cursor/skills/pocp-vault/` |
| Mesh-0 | `pocp-agent-mesh-0` | `pocp-mesh` | `.cursor/skills/pocp-mesh/` |
| Pulse-0 | `pocp-agent-pulse-0` | `pocp-pulse` | `.cursor/skills/pocp-pulse/` |
| Grid-0 | `pocp-agent-grid-0` | `pocp-grid` | `.cursor/skills/pocp-grid/` |
| Prism-0 | `pocp-agent-prism-0` | `pocp-prism` | `.cursor/skills/pocp-prism/` |
| Canvas-0 | `pocp-agent-canvas-0` | `pocp-canvas` | `.cursor/skills/pocp-canvas/` |
| Sentinel-0 | `pocp-agent-sentinel-0` | `pocp-sentinel` | `.cursor/skills/pocp-sentinel/` |
| Gauge-0 | `pocp-agent-gauge-0` | `pocp-gauge` | `.cursor/skills/pocp-gauge/` |
| Pipeline-0 | `pocp-agent-pipeline-0` | `pocp-pipeline` | `.cursor/skills/pocp-pipeline/` |
| Compass-0 | `pocp-agent-compass-0` | `pocp-compass` | `.cursor/skills/pocp-compass/` |
| Lex-0 | `pocp-agent-lex-0` | `pocp-lex` | `.cursor/skills/pocp-lex/` |
| Herald-0 | `pocp-agent-herald-0` | `pocp-herald` | `.cursor/skills/pocp-herald/` |

**Runtime witnesses** (not Meta): `pocp-entity-lumen-0`, `pocp-entity-desui`, `pocp-entity-clarion-0` — see `agents/prompts/runtime.md`.

## Agent Studio sub-platform

Self-learning orchestration: missions, handoffs, outcomes, improvement proposals.

- Docs: [docs/architecture/10-AGENT-STUDIO.md](../docs/architecture/10-AGENT-STUDIO.md)
- API: `GET /api/v1/agent-studio/dashboard`
- UI: **Agent Studio** tab in the dashboard

## Register / refresh Entities

Runs automatically on API startup (`ensure_genesis_entities` → `ensure_meta_agents`).

```bash
# CLI
python backend/scripts/ensure_meta_agents.py

# HTTP
curl -X POST http://127.0.0.1:8000/api/v1/meta-agents/ensure
curl http://127.0.0.1:8000/api/v1/meta-agents
curl http://127.0.0.1:8000/api/v1/meta-agents/pocp-agent-forge-0
```

## Sync Cursor Skills

After editing `meta_agents_spec.py` or prompts:

```bash
python agents/sync_cursor_skills.py
```

## Hierarchy

```text
Anchor-H (human)
    └── Nexus-0 (orchestrator)
            ├── Atlas, Forge, Vault, Mesh, Pulse, Grid, Prism
            ├── Canvas, Sentinel, Gauge, Pipeline
            └── Compass, Lex, Herald
```

All Meta Agents except Nexus report to `pocp-agent-nexus-0`. Nexus escalates deploy/secrets/disputes to Anchor-H.

## Governance

- Meta Agents **build** the platform; they do **not** alone finalize CP/AI Credits on live contributions.
- `Agent.config.decision_boundary` = `engineering_only_no_rights_finalization`
- Owner/maintainer: **PoCP AI Commons** organization entity (when present)
