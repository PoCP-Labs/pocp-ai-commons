# PoCP AI Commons — Backend

FastAPI service implementing **PoCP Protocol Spec V0.1** (entity-centric model).

**Database:** PostgreSQL (production / Docker). SQLite optional for local dev. See [docs/DATABASE.md](../docs/DATABASE.md).

## Run with Docker (recommended)

From repository root:

```bash
docker compose up --build
```

Starts PostgreSQL, applies Alembic migrations, seeds genesis entities and the demo scenario.

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

## Migrations

```bash
alembic revision --autogenerate -m "your change"
alembic upgrade head
```

## API

- Health: `GET /health` (includes `database.dialect` and status)
- Spec: [PROTOCOL-SPEC-v0.1.md](../PROTOCOL-SPEC-v0.1.md)
- Schema: [docs/SCHEMA.md](../docs/SCHEMA.md)

## Smoke test

With the server running:

```bash
python scripts/smoke_test.py http://127.0.0.1:8000
```

## Core loop

```text
POST /api/v1/contributions
POST /api/v1/contributions/{id}/verify
POST /api/v1/contributions/{id}/approve
```
