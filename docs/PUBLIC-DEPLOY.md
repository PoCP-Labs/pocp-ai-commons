# Public deployment guide

How to run **PoCP AI Commons** on the public internet (full stack: API + PostgreSQL + React UI).

For local development only, see [LOCAL-SETUP.md](./LOCAL-SETUP.md).

For a **static manifesto site** without the live app, see [GITHUB-PAGES.md](./GITHUB-PAGES.md) and [DEPLOY-CHECKLIST.md](./DEPLOY-CHECKLIST.md).

---

## What you are deploying

| Layer | Public URL (example) | Process |
|-------|----------------------|---------|
| Frontend | `https://app.your-domain.com` | Nginx serving Vite build (port 3000 on host) |
| API | `https://api.your-domain.com` | FastAPI / Uvicorn (port 8000 on host) |
| Database | **not public** | PostgreSQL 16 inside Docker only |
| TLS | Caddy or Nginx on host | Terminates HTTPS, reverse-proxies to 3000/8000 |

```text
Browser ──HTTPS──► Caddy (443)
                    ├─ app.*  → localhost:3000 (frontend container)
                    └─ api.*  → localhost:8000 (backend container)
                                      └─ postgres (Docker network only)
```

---

## Prerequisites

- A VPS or cloud VM (Ubuntu 22.04+ recommended) with a public IPv4 address.
- A domain name and DNS control.
- Docker Engine + Docker Compose plugin installed on the server.
- Firewall: allow **80** and **443**; do **not** expose **5432** publicly.

Recommended DNS:

| Host | Type | Value |
|------|------|-------|
| `api.your-domain.com` | A | server IP |
| `app.your-domain.com` | A | server IP |

Use the branch that contains Sprint Alpha features (e.g. `community-launch-pack`) until merged to `main`.

---

## Step 1 — Clone and configure

```bash
git clone https://github.com/PoCP-Labs/pocp-ai-commons.git
cd pocp-ai-commons
git checkout community-launch-pack   # or main after merge
```

### Project-root `.env` (Compose build variables)

```bash
cp deploy/.env.production.example .env
```

Edit `.env`:

```bash
POSTGRES_PASSWORD=<strong-password>
VITE_API_URL=https://api.your-domain.com
```

Generate a password:

```bash
openssl rand -hex 16
```

### Backend `backend/.env` (application secrets)

```bash
cp backend/.env.production.example backend/.env
```

Edit `backend/.env` — **must align** with public URLs and Postgres password:

| Variable | Production value |
|----------|------------------|
| `BACKEND_URL` | `https://api.your-domain.com` |
| `FRONTEND_URL` | `https://app.your-domain.com` |
| `JWT_SECRET` | `openssl rand -hex 32` |
| `DATABASE_URL` | `postgresql+psycopg://pocp:<POSTGRES_PASSWORD>@postgres:5432/pocp` |
| `GITHUB_OAUTH_CALLBACK_URL` | `https://api.your-domain.com/api/v1/auth/github/callback` |
| `ENABLE_DEV_LOGIN` | `false` |

---

## Step 2 — Start the production stack

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

What `docker-compose.prod.yml` changes vs local dev:

- PostgreSQL **not** published to the host.
- Backend runs **without** `--reload` and without source bind-mounts.
- Frontend is **built** with `VITE_API_URL` and served by **Nginx** on container port 80 → host **3000**.

Check containers:

```bash
docker compose ps
curl -s http://127.0.0.1:8000/health | jq .
```

Expected: `"status": "ok"`, `"database": { "dialect": "postgresql", "status": "ok" }`.

Open on the server (before TLS): `http://127.0.0.1:3000`.

---

## Step 3 — HTTPS with Caddy (recommended)

On the **host** (not inside Docker):

```bash
sudo apt install -y caddy
sudo cp deploy/Caddyfile.example /etc/caddy/Caddyfile
# Edit api/app hostnames and email, then:
sudo systemctl enable --now caddy
sudo systemctl reload caddy
```

Example `Caddyfile` is in [deploy/Caddyfile.example](../deploy/Caddyfile.example).

Caddy will obtain Let's Encrypt certificates when:

- DNS points to this server.
- Ports 80/443 are reachable from the internet.

Verify:

```bash
curl -s https://api.your-domain.com/health
```

Open `https://app.your-domain.com` in a browser.

### Nginx alternative

If you prefer Nginx, terminate TLS there and `proxy_pass` to `127.0.0.1:8000` and `127.0.0.1:3000` with the same hostnames as in the Caddy example.

---

## Step 4 — GitHub OAuth (public login)

1. GitHub → **Settings → Developer settings → OAuth Apps → New OAuth App**
2. **Homepage URL:** `https://app.your-domain.com`
3. **Authorization callback URL:** `https://api.your-domain.com/api/v1/auth/github/callback`
4. Copy Client ID and Secret into `backend/.env`
5. Restart backend:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml restart backend
```

With `ENABLE_DEV_LOGIN=false`, users must use **GitHub Login** on the public site.

---

## Step 5 — Smoke test

From your laptop (replace the API host):

```bash
cd backend
python scripts/smoke_test.py https://api.your-domain.com
```

Note: the default smoke test uses **dev-login**. For production, either temporarily set `ENABLE_DEV_LOGIN=true` on a staging host, or test manually via GitHub Login in the UI.

---

## Production security checklist

- [ ] `POSTGRES_PASSWORD` and `JWT_SECRET` are strong random values, not repo defaults.
- [ ] `ENABLE_DEV_LOGIN=false` on the public internet.
- [ ] Port **5432** is not mapped on the host (`docker-compose.prod.yml` removes it).
- [ ] HTTPS on both `api.*` and `app.*`.
- [ ] GitHub OAuth callback uses `https://`.
- [ ] `OPENAI_API_KEY` / `DEEPSEEK_API_KEY` only in `backend/.env`, never committed.
- [ ] Firewall allows only 22 (SSH), 80, 443 as needed.
- [ ] Optional: restrict SSH, enable automatic security updates, off-site DB backups.

---

## Updates and rollback

**Pull and rebuild:**

```bash
git pull
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

Alembic migrations run automatically on API startup (`init_db()`).

**View logs:**

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f backend
```

**Reset demo data (destructive):**

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec backend python scripts/reset_db.py
docker compose -f docker-compose.yml -f docker-compose.prod.yml restart backend
```

---

## Static site only (no live app)

To publish manifesto / whitepaper HTML without running the API:

1. Merge docs + `.github/workflows/pages.yml` to `main`.
2. GitHub repo **Settings → Pages → Source: GitHub Actions**.
3. Site serves from the `docs/` folder (see [DEPLOY-CHECKLIST.md](./DEPLOY-CHECKLIST.md)).

This does **not** include login, AI Chat, or the contribution loop.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Frontend calls `localhost:8000` | Rebuild frontend: `VITE_API_URL` must be set in project-root `.env` before `docker compose ... build` |
| OAuth redirect error | `GITHUB_OAUTH_CALLBACK_URL`, `FRONTEND_URL`, and GitHub App settings must match exactly (HTTPS) |
| `database status: error` | Wait for Postgres healthy; check `DATABASE_URL` password matches `POSTGRES_PASSWORD` |
| 502 from Caddy | Ensure stack is up: `curl http://127.0.0.1:8000/health` |
| Cannot approve own contribution | Use a second GitHub account as reviewer (by design) |

---

## File reference

| File | Purpose |
|------|---------|
| [docker-compose.prod.yml](../docker-compose.prod.yml) | Production overrides |
| [deploy/.env.production.example](../deploy/.env.production.example) | Root `.env` template |
| [backend/.env.production.example](../backend/.env.production.example) | API secrets template |
| [deploy/Caddyfile.example](../deploy/Caddyfile.example) | HTTPS reverse proxy |
| [backend/Dockerfile.prod](../backend/Dockerfile.prod) | API image (no reload) |
| [frontend/Dockerfile.prod](../frontend/Dockerfile.prod) | Build + Nginx static image |

---

## Related

- [DATABASE.md](./DATABASE.md) — PostgreSQL and migrations
- [PUBLIC-DEMO.md](./PUBLIC-DEMO.md) — demo script for visitors
- [ARCHITECTURE.md](./ARCHITECTURE.md) — system overview
