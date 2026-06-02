# Local Setup

How to run PoCP AI Commons on your machine.

## Prerequisites

- Python 3.11+
- Node.js 18+ (frontend)
- Optional: Docker Desktop (PostgreSQL + full stack)

## Option A — Quick local (SQLite, no Docker)

**Backend:**

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
# Set DATABASE_URL=sqlite:///./data/pocp.db in .env
set POCP_WAIT_FOR_DB=false          # Windows
export POCP_WAIT_FOR_DB=false       # macOS/Linux
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

**Frontend:**

```bash
cd frontend
npm install
set VITE_API_URL=http://localhost:8000   # Windows
npm run dev
```

Open http://localhost:3000 · API docs http://localhost:8000/docs

## Option C — Phase A one-command (recommended for acceptance)

Validates the **demonstrable public loop** (smoke + optional federation):

```powershell
# Windows — single node (:8000)
.\scripts\run-phase-a.ps1

# Windows — federation (node-a :8100, node-b :8101)
.\scripts\run-phase-a.ps1 -Federation
```

```bash
# Linux / macOS — single node
./scripts/run-phase-a.sh

# Federation
./scripts/run-phase-a.sh --federation
```

Acceptance only (stack already running):

```bash
python backend/scripts/run_phase_a_acceptance.py http://127.0.0.1:8000
python backend/scripts/run_phase_a_acceptance.py http://127.0.0.1:8100 --federation http://127.0.0.1:8101
```

**Federation preflight only** (trust bundle + `validate-proof`, no import):

```bash
docker compose -f docker-compose.federation.yml up -d --build
python backend/scripts/federation_pilot_preflight.py
python backend/scripts/federation_pilot_preflight.py --sync   # preflight + sync on Node B
python backend/scripts/run_entity_pilot_demo.py              # full pilot orchestration
```

**Strict trust policy (production-like import gates on Node B):**

```bash
docker compose -f docker-compose.federation.yml -f docker-compose.federation.strict.yml up -d backend-b
python backend/scripts/federation_strict_mode_test.py
```

See [ROADMAP-THREE-PHASES.md](./ROADMAP-THREE-PHASES.md) for Phase A/B/C exit criteria.

**Local optimization (P0 — Exchange Spine + Wallet):** federation acceptance includes `federation_exchange_demo_test.py` and wallet audit:

```bash
python backend/scripts/run_phase_a_acceptance.py http://127.0.0.1:8100 --federation http://127.0.0.1:8101
```

Protocol v0.4 index: [protocol/README.md](./protocol/README.md) · Exchange Spine: [protocol/EXCHANGE-SPINE-v0.1.md](./protocol/EXCHANGE-SPINE-v0.1.md) · Entity Dialogue: [protocol/ENTITY-DIALOGUE-PROTOCOL.md](./protocol/ENTITY-DIALOGUE-PROTOCOL.md).

### Entity Dialogue API (protocol layer L2)

Native envelope: `pocp.entity_dialogue.v0.1` — see [ENTITY-DIALOGUE-PROTOCOL.md](./protocol/ENTITY-DIALOGUE-PROTOCOL.md). Agent Studio mission: [agents/missions/protocol-layer-edp/MANIFEST.md](../agents/missions/protocol-layer-edp/MANIFEST.md).

**Public manifest** (no auth):

```bash
curl -s http://127.0.0.1:8000/api/v1/intelligence/protocol/entity-dialogue | jq .
# Docker Compose host port: http://127.0.0.1:8008/...
```

**Ping dialogue** (requires session — dev-login first, then Bearer token):

```bash
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/v1/auth/dev-login \
  -H "Content-Type: application/json" \
  -d '{"username":"rain","email":"rain@example.com"}' | jq -r .access_token)

curl -s -X POST http://127.0.0.1:8000/api/v1/intelligence/dialogue \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "schema": "pocp.entity_dialogue.v0.1",
    "dialogue_id": "dlg_ping_local_1",
    "kind": "ping",
    "from": { "entity_id": "pocp-entity-rain", "node_id": "local" },
    "to": { "entity_id": "pocp-entity-rain", "node_id": "local" }
  }' | jq .
```

**Protocol layer tests** (stack not required):

```bash
cd backend && python -m pytest -q tests/test_entity_dialogue.py
```

**Proof deep-link (UI):** open `http://localhost:3000/?proof=<contribution_id>` to verify a contribution proof without running the full submit flow.

## Meta Agents & Agent Studio (engineering orchestration)

PoCP registers **15 Meta Agents** as protocol Entities for Cursor-based development orchestration.

```bash
# Register / refresh Meta Agent entities
python backend/scripts/ensure_meta_agents.py

# Agent Studio API (stack running)
curl http://127.0.0.1:8008/api/v1/agent-studio/dashboard
curl http://127.0.0.1:8008/api/v1/meta-agents
```

| Resource | Purpose |
|----------|---------|
| Dashboard **Agent Studio** tab | Missions, handoffs, Nexus autopilot, outcomes |
| [agents/WORKFLOW.md](../agents/WORKFLOW.md) | Start a mission + handoffs |
| [architecture/10-AGENT-STUDIO.md](./architecture/10-AGENT-STUDIO.md) | Sub-platform architecture |
| [agents/META-AGENTS.md](../agents/META-AGENTS.md) | Entity IDs and Cursor skill sync |
| [agents/CURSOR-AUTOMATION.md](../agents/CURSOR-AUTOMATION.md) | Cursor SDK bridge for live handoff execution |

After editing agent specs or prompts: `python agents/sync_cursor_skills.py`

**Live handoffs (optional):** set `POCP_CURSOR_AUTOMATION=true` and `CURSOR_API_KEY` — see [CURSOR-AUTOMATION.md](../agents/CURSOR-AUTOMATION.md).

## Option B — Docker Compose (PostgreSQL)

```bash
docker compose up --build
```

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| API | http://localhost:8008 (host maps to container :8000) |
| PostgreSQL | localhost:5432 (pocp/pocp) |

Federation stack (optional) uses **8100** / **8101** — see `docker-compose.federation.yml`.

## Smoke test

With the API running:

```bash
cd backend
python scripts/smoke_test.py
# Or against custom URL:
python scripts/smoke_test.py http://127.0.0.1:8008
```

Expected output ends with: `OK Sprint Alpha loop: login → chat → auto-verify → approve → proof → ledger → federation`

## Environment variables

See `backend/.env.example`. Key settings:

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | SQLite or PostgreSQL connection |
| `GITHUB_CLIENT_ID/SECRET` | GitHub OAuth (optional) |
| `OPENAI_API_KEY` / `DEEPSEEK_API_KEY` | Real AI verifiers (optional; mock fallback) |
| `ENABLE_DEV_LOGIN` | Local dev login (default true) |
| `FRONTEND_URL` | OAuth redirect target (default http://localhost:3000) |

## Dev login personas (dashboard)

On http://localhost:3000, use the **persona** dropdown next to **Dev Login**:

| Persona | Use for |
|---------|---------|
| **Rain** | Founder (`pocp-entity-rain`), org sponsor, Genesis manifesto author |
| **Bob** | Governance proxy, optional human finalizer on demo contribution |
| **New guest** | Random Human entity (explore signup flow) |

Equivalent API:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/auth/dev-login \
  -H "Content-Type: application/json" \
  -d '{"username":"rain","email":"rain@example.com"}'
```

Production public sites should set `ENABLE_DEV_LOGIN=false` and use GitHub OAuth only. See [LANGUAGE-POLICY.md](./LANGUAGE-POLICY.md).

## Common issues (Windows)

**Port 8000 already in use:** Docker Compose publishes PoCP on **8008** by default (another app often binds 8000). Stop the conflicting container or change the host port in `docker-compose.yml`. For a bare `uvicorn` run, pick a free port:

```powershell
netstat -ano | findstr ":8000"
Stop-Process -Id <PID> -Force
```

**SQLite database locked:** Only one backend process should use the same `pocp.db`. Use a fresh file or stop duplicate uvicorn instances.

**Docker not running:** Use Option A (SQLite) or start Docker Desktop first.

**Backend container restart loop:** Check logs with `docker compose logs backend --tail 50`. Common cause: entity `id` longer than 36 characters in seed data (fixed for inspiration entities as `pocp-insp-*`). Reset if needed: `docker compose down` then `docker compose up --build`.

**`docker compose up --build` slow or TLS timeout:** Docker Hub mirror/network issue; retry or build without `--build` if images exist.

**Inspiration entities missing after upgrade:** Restart backend after pulling; startup runs `ensure_inspiration_entities`.

## Public deployment

To expose the full stack on the internet (HTTPS, production Compose, Caddy), see [PUBLIC-DEPLOY.md](./PUBLIC-DEPLOY.md).

For a **30–100 user pilot** after staging works, see [PILOT-LAUNCH-CHECKLIST.md](./PILOT-LAUNCH-CHECKLIST.md).

## Next steps

- [Entity Dialogue Protocol](./protocol/ENTITY-DIALOGUE-PROTOCOL.md) — L2 native envelope + API examples above
- [Three-Phase Roadmap (Phase A/B/C)](./ROADMAP-THREE-PHASES.md) — **primary execution path**
- [Public Deploy](./PUBLIC-DEPLOY.md)
- [Pilot Launch Checklist](./PILOT-LAUNCH-CHECKLIST.md)
- [API Spec](./API-SPEC.md)
- [Architecture](./ARCHITECTURE.md)
- [Sprint Alpha](./SPRINT_ALPHA.md)
- [Roadmap](../ROADMAP.md) — legacy product phases
