# Agent Studio → Cursor Full Automation

Agent Studio can execute pending **handoffs** through the [Cursor SDK](https://cursor.com/docs/sdk/python) so Meta Agents write code without you opening the IDE manually.

## Architecture

```text
Nexus autopilot → pending handoffs in Postgres
       ↓
Cursor worker (host or backend loop)
       ↓
cursor-sdk Agent.prompt(local cwd = repo root)
       ↓
complete handoff + record outcome → Nexus follow-up tick
```

## Setup (Windows — recommended)

1. Use **Python 3.12+** on the host (`py -3.12`). The Cursor SDK bridge requires `os.get_blocking` (not available on 3.11). PoCP ships a **threaded bridge launcher** for Windows because `cursor-sdk` 0.1.x uses `select()` on stderr pipes, which raises `WinError 10038`.

   ```powershell
   py -3.12 -m pip install cursor-sdk python-dotenv
   ```

2. Create API key: [Cursor Dashboard → Integrations](https://cursor.com/dashboard/integrations)

3. Start stack:

   ```powershell
   docker compose up -d postgres backend frontend
   ```

4. Run the **host worker** (full repo + local Cursor):

   ```powershell
   $env:CURSOR_API_KEY = "cursor_..."
   $env:POCP_CURSOR_AUTOMATION = "true"
   $env:POCP_REPO_ROOT = "D:\pocp-ai-commons"
   $env:DATABASE_URL = "postgresql+psycopg://pocp:pocp@127.0.0.1:5435/pocp"
   .\scripts\run-studio-cursor-trial.ps1
   ```

   Or one shot:

   ```powershell
   $env:POCP_CURSOR_WORKER_ONCE = "true"
   .\scripts\run-studio-cursor-worker.ps1
   ```

## Setup (Docker backend loop)

1. `pip install cursor-sdk` in backend image (or mount venv).
2. In `docker-compose.yml` for `backend`:

   ```yaml
   environment:
     CURSOR_API_KEY: "cursor_..."
     POCP_CURSOR_AUTOMATION: "true"
     POCP_CURSOR_AUTOMATION_INTERVAL_SEC: "300"
     POCP_REPO_ROOT: "/workspace"
   ```

3. `docker compose restart backend` — background loop runs every interval.

## Environment variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `CURSOR_API_KEY` | — | Required |
| `POCP_CURSOR_AUTOMATION` | `false` | Enable automation |
| `POCP_CURSOR_AUTOMATION_INTERVAL_SEC` | `300` | Loop interval |
| `POCP_CURSOR_AUTOMATION_MAX_PER_TICK` | `1` | Handoffs per tick |
| `POCP_REPO_ROOT` | repo root | Local agent cwd |
| `POCP_CURSOR_RUNTIME` | `local` | `local` or `cloud` |
| `POCP_CURSOR_MODEL` | `composer-2.5` | Model id |
| `POCP_CURSOR_CLOUD_REPO` | — | Required if runtime=cloud |
| `POCP_CURSOR_AUTO_PR` | `false` | Cloud PR creation |

## Nexus super-loop (human-out-of-loop target)

When `POCP_NEXUS_SUPER_LOOP=true`, the backend runs a **single background task** that replaces the Cursor-only loop:

1. **Probe** — DB + API health
2. **Plan** — Nexus autopilot (missions + handoffs = “AR” dispatch)
3. **Do** — up to `POCP_SUPER_LOOP_MAX_CURSOR_PER_TICK` Cursor handoffs
4. **Check** — optional `POCP_SUPER_LOOP_RUN_ACCEPTANCE=true` → Phase A script
5. **Act** — Nexus learning cycle (coach, proposals)
6. **Heal** — failed health → Gauge-0 + Sentinel-0 repair handoffs

| Variable | Default | Purpose |
|----------|---------|---------|
| `POCP_NEXUS_SUPER_LOOP` | `false` | Enable super-loop background task |
| `POCP_NEXUS_SUPER_LOOP_INTERVAL_SEC` | `600` | Tick interval |
| `POCP_SUPER_LOOP_MAX_CURSOR_PER_TICK` | `2` | Cursor handoffs per tick |
| `POCP_SUPER_LOOP_RUN_ACCEPTANCE` | `false` | Run Phase A acceptance subprocess |

Manual tick (UI **Run super-loop tick** or API):

```http
GET  /api/v1/agent-studio/nexus/super-loop/status
GET  /api/v1/agent-studio/nexus/super-loop/last
POST /api/v1/agent-studio/nexus/super-tick?max_cursor_handoffs=2
```

### Windows + Docker (recommended)

Docker runs API + Postgres; **Cursor runs on the host** (avoids `WinError 10038` in containers).

`backend/.env`:

```env
POCP_NEXUS_AUTOPILOT=true
POCP_CURSOR_AUTOMATION=true
CURSOR_API_KEY=cursor_...
POCP_NEXUS_SUPER_LOOP_HOST=true
POCP_NEXUS_SUPER_LOOP=false
POCP_REPO_ROOT=D:\pocp-ai-commons
BACKEND_URL=http://localhost:8008
POCP_NEXUS_SUPER_LOOP_INTERVAL_SEC=600
POCP_SUPER_LOOP_MAX_CURSOR_PER_TICK=2
```

```powershell
docker compose up -d
.\scripts\run-studio-super-loop-trial.ps1   # one verbose tick
.\scripts\run-studio-super-loop.ps1         # continuous loop
```

### Linux / all-in-Docker

```env
POCP_NEXUS_SUPER_LOOP=true
POCP_NEXUS_SUPER_LOOP_HOST=false
```

Rebuild `backend` after changing `.env`.

## API

```http
GET  /api/v1/agent-studio/cursor/status
GET  /api/v1/agent-studio/cursor/pending
POST /api/v1/agent-studio/cursor/run?max_handoffs=1
```

## Boundaries

- Handoffs assigned to **Nexus-0** are not sent to Cursor (PM only).
- Does not auto-commit git; review diffs before merge.
- Does not finalize CP/AI Credits on live contributions.
- Requires valid API key and billable Cursor agent minutes.

## Visible trial (see live output in terminal)

```powershell
.\scripts\run-studio-cursor-trial.ps1
```

Or:

```powershell
python backend/scripts/run_studio_cursor_worker.py --verbose --once
```

You will see: Nexus dispatch → handoff picked → Cursor assistant streaming text → completed/blocked.

## UI

**Agent Studio** → **Cursor — Full code automation** shows status and **Run Cursor on next handoff**.
