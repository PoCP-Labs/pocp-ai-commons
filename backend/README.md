# PoCP AI Commons — Backend

FastAPI service implementing **PoCP Protocol Spec V0.1** (entity-centric model).

**Database:** PostgreSQL (production / Docker). SQLite optional for local dev. See [docs/DATABASE.md](../docs/DATABASE.md).

## Run with Docker (recommended)

From repository root:

```bash
docker compose up --build
```

Starts PostgreSQL, applies Alembic migrations, seeds genesis entities and the demo scenario.

**Production / public internet:** [docs/PUBLIC-DEPLOY.md](../docs/PUBLIC-DEPLOY.md) and `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build`.

## Run locally

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env   # set DATABASE_URL (PostgreSQL or SQLite)
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

On first start, the API:

1. Waits for the database (PostgreSQL)
2. Runs Alembic migrations to `head`
3. Upserts genesis LLM entities **Lumen-0** and **DeSui**
4. Seeds the **R Language Study Materials** demo if empty

Reset demo data:

```bash
python scripts/reset_db.py
# then restart uvicorn or docker compose
```

Upgrade an **existing** database to the extended Entity ontology (Tool, Dataset, witness role on demo contribution) without wiping data:

```bash
python scripts/upgrade_demo_topology.py
# or restart the API — seed_demo runs the same upgrade on startup
```

Distributed compute Phase α (Entity `compute_profile`, scheduler, receipts):

```bash
python scripts/distributed_compute_demo_test.py http://127.0.0.1:8000
```

See [docs/DISTRIBUTED-COMPUTE-RESEARCH.md](../docs/DISTRIBUTED-COMPUTE-RESEARCH.md).

## Migrations

```bash
alembic revision --autogenerate -m "your change"
alembic upgrade head
```

## API

- Health: `GET /health` (includes `database.dialect` and status)
- Spec: [PROTOCOL-SPEC-v0.1.md](../PROTOCOL-SPEC-v0.1.md)
- Schema: [docs/SCHEMA.md](../docs/SCHEMA.md)
- Capability integration: [docs/CAPABILITY-INTEGRATION.md](../docs/CAPABILITY-INTEGRATION.md)

### Capability import (required platform layer)

```text
GET  /api/v1/capabilities/sources
GET  /api/v1/capabilities/catalog
POST /api/v1/capabilities/import/agentskills
POST /api/v1/capabilities/import/agent
POST /api/v1/capabilities/skills/{skill_entity_id}/execute
POST /api/v1/capabilities/agents/{agent_entity_id}/execute
POST /api/v1/capabilities/{entity_id}/runtime
POST /api/v1/capabilities/{entity_id}/activate
```

Bundled OpenClaw-compatible example skills sync on startup (`config/capabilities/bundled/`).

Smoke test (server running):

```bash
python scripts/capability_execute_test.py http://127.0.0.1:8000
```

## Smoke test

With the server running:

```bash
python scripts/smoke_test.py http://127.0.0.1:8000
```

## Pilot metrics & tasks

Entity Network Pilot dashboard (protocol · intelligence · compute layers):

```bash
python scripts/pilot_metrics.py http://127.0.0.1:8000
python scripts/pilot_metrics.py --json
python scripts/run_entity_pilot_demo.py --single http://127.0.0.1:8000
```

Seed 10 Epic B task templates:

```bash
python scripts/seed_pilot_tasks.py --api http://127.0.0.1:8000
python scripts/run_entity_pilot_demo.py --single http://127.0.0.1:8000 --seed-tasks
```

Epic D two-node federation: `docker compose -f docker-compose.federation.yml up -d` then `python scripts/run_entity_pilot_demo.py`.

See [docs/PILOT-LAUNCH-CHECKLIST.md](../docs/PILOT-LAUNCH-CHECKLIST.md) · [docs/FEDERATION-DEMO.md](../docs/FEDERATION-DEMO.md).

## Core loop

```text
POST /api/v1/contributions
POST /api/v1/contributions/{id}/verify
POST /api/v1/contributions/{id}/approve
```
