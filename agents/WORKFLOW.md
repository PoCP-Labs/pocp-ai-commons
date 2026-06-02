# Agent Studio — Start Working

## 1. Boot

```bash
python backend/scripts/ensure_meta_agents.py
.\scripts\run-phase-a.ps1   # or your API stack
```

Open UI → **Agent Studio** tab → **Register Meta Agents** (idempotent).

## 2. Start an evolution mission

**Fast path (UI):** Agent Studio → **Phase A P0** or **Phase A Full** — creates mission + spawns all Nexus handoffs.

**Fast path (API):**

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/agent-studio/missions/from-plan/phase_a_p0"
curl -X POST "http://127.0.0.1:8000/api/v1/agent-studio/missions/from-plan/protocol_layer_edp"
```

**Protocol layer track (Entity Dialogue L2):**

```powershell
.\scripts\dispatch-protocol-layer-studio.ps1 -IssuesDryRun
.\scripts\dispatch-protocol-layer-studio.ps1 -CreateIssues -CursorTick
# or
python backend/scripts/dispatch_protocol_layer_studio.py --create-issues --cursor-tick
```

See [agents/missions/protocol-layer-edp/MANIFEST.md](./missions/protocol-layer-edp/MANIFEST.md).

**Custom mission:** enter title + kind → **Activate**.

```bash
curl -X POST http://127.0.0.1:8000/api/v1/agent-studio/missions \
  -H "Content-Type: application/json" \
  -d '{"title":"Phase A P0","kind":"improve","orchestrator_entity_id":"pocp-agent-nexus-0"}'
curl -X POST http://127.0.0.1:8000/api/v1/agent-studio/missions/{id}/activate
curl -X POST "http://127.0.0.1:8000/api/v1/agent-studio/missions/{id}/spawn-handoffs?plan_id=phase_a_p0"
```

## 3. Full automation (Cursor SDK)

See **[CURSOR-AUTOMATION.md](./CURSOR-AUTOMATION.md)** — host worker or Docker loop executes handoffs without opening the IDE.

```powershell
pip install cursor-sdk
$env:CURSOR_API_KEY = "cursor_..."
.\scripts\run-studio-cursor-worker.ps1
```

## 4. Manual Cursor: Nexus dispatches work

Paste into main Agent (Skill: `pocp-nexus`):

```markdown
Mission {mission_id} is active. Break Phase A P0 into handoffs per agents/ROSTER.md.
For each subtask, output a Handoff block and POST payload for /api/v1/agent-studio/handoffs.
```

## 4. Domain agents implement + handoff

Sub-agent (e.g. Vault-0). After work:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/agent-studio/handoffs \
  -d '{"from_agent_entity_id":"pocp-agent-vault-0","to_agent_entity_id":"pocp-agent-nexus-0","mission_id":"...","scope":"wallet audit fix","tests_run":"pytest -k wallet"}'
```

## 5. Record outcome (Learn)

```bash
curl -X POST http://127.0.0.1:8000/api/v1/agent-studio/outcomes \
  -d '{"agent_entity_id":"pocp-agent-vault-0","kind":"acceptance","result":"fail","summary":"wallet audit red","auto_evaluate":true}'
```

Auto-creates an **improvement proposal** when `auto_evaluate=true`.

## 6. Review & apply (Transform / Improve)

In **Agent Studio** UI: **Approve** → **Apply** (updates `learning_profile`, bumps `evolution_version`).

Reviewer entity: `pocp-agent-gauge-0` or your human Entity id.

## 7. Grow

Three consecutive `pass` outcomes on the same `kind` → auto **grow** proposal (capability_add).

## Self-* mapping

| Ability | Studio mechanism |
|---------|------------------|
| Self-learning | `outcomes` table + learning_profile stats |
| Self-growth | pass-streak → capability_add proposals |
| Self-transformation | approved proposals → apply to Agent.config |
| Self-improvement | fail outcomes → refine proposals |

Code changes still flow through **git + Anchor-H**; Studio does not auto-commit.

## CI auto-learning

`smoke-test.yml` reports pytest + acceptance results to Agent Studio (Gauge-0 outcomes).

Local:

```bash
python backend/scripts/report_agent_studio_ci.py \
  --api http://127.0.0.1:8000 \
  --pytest-exit 0 \
  --acceptance-exit 0
```

## v1.2 — Handoff complete, patches, graph

- UI: **Complete** / **Blocked** on pending handoffs
- **Apply** writes `agents/patches/{slug}-{id}.md` — merge into `agents/prompts/` by hand
- **Graph** tab: `studio` layer edges (`handoff_to`, `orchestrates`, `reports_to`)

```bash
GET /api/v1/agent-studio/proposals/{id}/patch-preview
```

See [docs/architecture/10-AGENT-STUDIO.md](../docs/architecture/10-AGENT-STUDIO.md).
