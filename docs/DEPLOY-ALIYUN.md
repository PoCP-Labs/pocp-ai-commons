# Deploy on Alibaba Cloud (ECS)

Run **PoCP AI Commons** on an Alibaba Cloud **ECS** instance with Docker Compose. For generic HTTPS, env, and staging gates, see [PUBLIC-DEPLOY.md](./PUBLIC-DEPLOY.md).

## Recommended topology

| Component | Alibaba service | Notes |
|-----------|-----------------|-------|
| App + API + DB | ECS (Ubuntu 22.04, 2 vCPU / 4 GiB+) | Single VM is enough for Phase A pilot |
| TLS | Application Load Balancer **or** Caddy/Nginx on ECS | Terminate HTTPS on 443 |
| DNS | Alibaba Cloud DNS | `A` records → ECS public IP |
| Secrets | `.env` on host (not in git) | Rotate `POSTGRES_PASSWORD`, `JWT_SECRET` |

Do **not** expose PostgreSQL (5432) on the public security group.

## 1. Create ECS

1. Console → **Elastic Compute Service** → create instance (Ubuntu 22.04).
2. **Security group**: allow inbound **22** (SSH, your IP only), **80**, **443**.
3. Attach an **Elastic IP** and note the public address.

## 2. Install Docker on the VM

```bash
sudo apt update && sudo apt install -y git docker.io docker-compose-v2
sudo usermod -aG docker $USER
# log out and back in
```

## 3. Clone and configure

```bash
git clone https://github.com/PoCP-Labs/pocp-ai-commons.git
cd pocp-ai-commons
git checkout graph-network-animation   # or your release tag

cp deploy/.env.production.example .env
cp backend/.env.staging.example backend/.env
```

Edit project-root `.env`:

```bash
POSTGRES_PASSWORD=<openssl rand -hex 16>
VITE_API_URL=https://api.your-domain.com
```

Edit `backend/.env`: set `DATABASE_URL`, `JWT_SECRET`, GitHub OAuth URLs, `ENABLE_DEV_LOGIN=false` for staging.

Verify before go-live:

```bash
python backend/scripts/verify_staging_env.py
```

## 4. Publish ports on ECS

Default Compose maps:

| Host port | Service |
|-----------|---------|
| 3000 | Frontend (dev server image) |
| 8008 | API (avoid 8000 conflicts on shared dev machines) |
| 5432 | Postgres — **bind to Docker network only** in production |

For production, prefer **only 80/443** on the host and reverse-proxy to containers — see [PUBLIC-DEPLOY.md](./PUBLIC-DEPLOY.md) Caddy example. Map `api.*` → backend `8008` (or internal `8000` inside the container).

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

## 5. DNS (Alibaba Cloud DNS)

| Record | Type | Value |
|--------|------|-------|
| `api.your-domain.com` | A | ECS Elastic IP |
| `app.your-domain.com` | A | ECS Elastic IP |

## 6. Acceptance

```bash
curl -s https://api.your-domain.com/health | jq .
python backend/scripts/run_phase_a_acceptance.py https://api.your-domain.com --staging --skip-optional
```

Local smoke (on the VM):

```bash
cd backend && python scripts/smoke_test.py http://127.0.0.1:8008
```

## 7. Optional Alibaba services (later)

| Need | Service |
|------|---------|
| Managed Postgres | ApsaraDB RDS PostgreSQL 16 |
| Object storage for proof exports | OSS + `POCP_EXPORT_BUCKET` (custom) |
| CDN for static frontend | CDN + OSS static site |
| Monitoring | ARMS or self-hosted Prometheus |

Phase A does not require RDS; Docker Postgres on ECS is sufficient for pilots.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| UI shows zeros / `Not Found` | `curl http://127.0.0.1:8008/health` — must return `"service":"pocp-ai-commons"`. Rebuild frontend with correct `VITE_API_URL`. |
| Port 8008 in use | Change host mapping in `docker-compose.yml` and `.env` consistently. |
| OAuth redirect mismatch | `GITHUB_OAUTH_CALLBACK_URL` must match public `https://api.../api/v1/auth/github/callback`. |

See also [LOCAL-SETUP.md](./LOCAL-SETUP.md) · [PILOT-LAUNCH-CHECKLIST.md](./PILOT-LAUNCH-CHECKLIST.md).
