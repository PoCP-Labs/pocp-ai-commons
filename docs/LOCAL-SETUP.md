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

## Option B — Docker Compose (PostgreSQL)

```bash
docker compose up --build
```

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| API | http://localhost:8000 |
| PostgreSQL | localhost:5432 (pocp/pocp) |

## Smoke test

With the API running:

```bash
cd backend
python scripts/smoke_test.py
# Or against custom URL:
python scripts/smoke_test.py http://127.0.0.1:8000
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

**Port 8000 already in use:** Stop the old process or use another port:

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

- [Public Deploy](./PUBLIC-DEPLOY.md)
- [Pilot Launch Checklist](./PILOT-LAUNCH-CHECKLIST.md)
- [API Spec](./API-SPEC.md)
- [Architecture](./ARCHITECTURE.md)
- [Sprint Alpha](./SPRINT_ALPHA.md)
- [Roadmap](../ROADMAP.md)
