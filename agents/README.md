# PoCP Agent Kit

Multi-agent orchestration for PoCP AI Commons development.

| Artifact | Purpose |
|----------|---------|
| [ROSTER.md](./ROSTER.md) | Roles, paths, handoff matrix |
| [META-AGENTS.md](./META-AGENTS.md) | Entity IDs, API, skill sync |
| [WORKFLOW.md](./WORKFLOW.md) | Agent Studio — start working |
| [../docs/architecture/10-AGENT-STUDIO.md](../docs/architecture/10-AGENT-STUDIO.md) | Sub-platform architecture |
| [prompts/](./prompts/) | Copy-paste system prompts per agent |
| [../.cursor/skills/pocp-*](../.cursor/skills/) | Cursor Agent Skills (15 Meta Agents) |
| [../.cursor/rules/pocp-*.mdc](../.cursor/rules/) | Cursor rules (auto-apply by file glob) |
| [../backend/meta_agents_spec.py](../backend/meta_agents_spec.py) | Canonical registry spec |

## Quick start

1. **Register Entities** — `python backend/scripts/ensure_meta_agents.py` (or start API).
2. **Orchestrate** — Cursor Skill `pocp-nexus` or prompt `agents/prompts/nexus-0.md`.
3. **Implement** — domain skill (`pocp-forge`, `pocp-vault`, …); rules auto-activate on file globs.
4. **Verify** — **Gauge-0** before merge; **Lex-0** if user-facing economic language changed.
5. **Ship** — **Anchor-H** for secrets and staging go-live.

After spec changes: `python agents/sync_cursor_skills.py`

## Task labels (Cursor Task / subagent)

`pocp-nexus` · `pocp-atlas` · `pocp-forge` · `pocp-vault` · `pocp-mesh` · `pocp-pulse` · `pocp-grid` · `pocp-prism` · `pocp-canvas` · `pocp-sentinel` · `pocp-gauge` · `pocp-pipeline` · `pocp-compass` · `pocp-lex` · `pocp-herald`

## Runtime (do not use as coders)

[Lumen-0, DeSui, Clarion-0](./prompts/runtime.md) — witnesses inside the protocol; Meta agents call via APIs only.
