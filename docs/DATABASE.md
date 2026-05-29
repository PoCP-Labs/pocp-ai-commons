# Database — PostgreSQL-first

PoCP AI Commons uses **PostgreSQL** as the production database. **SQLite** remains available for quick local development without Docker.

## Why PostgreSQL

| Need | PostgreSQL | SQLite |
|------|------------|--------|
| Concurrent API writes | Connection pool, row-level locking | Single-writer bottleneck |
| Multi-instance deploy (Docker/K8s) | Shared server | File on one host only |
| JSON metadata at scale | JSONB + indexes | JSON only |
| Schema evolution | Alembic migrations | Same migrations, not for prod |
| Backups & ops | Standard tooling | Copy file (dev only) |

## Configuration

Set `DATABASE_URL` in `backend/.env` (copy from `backend/.env.example`):

```bash
# Docker Compose (default)
DATABASE_URL=postgresql+psycopg://pocp:pocp@localhost:5432/pocp

# Local SQLite (no Postgres)
DATABASE_URL=sqlite:///./data/pocp.db
```

Optional pool tuning (PostgreSQL only):

```bash
POCP_DB_POOL_SIZE=5
POCP_DB_MAX_OVERFLOW=10
POCP_WAIT_FOR_DB=true
POCP_WAIT_FOR_DB_SECONDS=60
```

## Run with Docker (recommended)

```bash
docker compose up --build
```

This starts **PostgreSQL 16**, runs **Alembic migrations** on API startup, then seeds genesis entities and the R-language demo if the database is empty.

## Run locally without Docker

1. Start PostgreSQL and create database `pocp` (user/password as in `.env.example`), **or** use SQLite URL above.
2. Install dependencies and run API:

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env   # edit DATABASE_URL if needed
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Migrations run automatically in the application lifespan (`init_db()` → `alembic upgrade head`).

## Migrations (Alembic)

Create a new revision after changing SQLAlchemy models:

```bash
cd backend
# set DATABASE_URL to your dev database
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```

Revision history lives in `backend/alembic/versions/`.

## Reset demo data

```bash
cd backend
python scripts/reset_db.py
# restart uvicorn or docker compose
```

- **SQLite**: deletes `backend/data/pocp.db`
- **PostgreSQL**: drops all tables and re-applies migrations

## Health check

`GET /health` includes database dialect and connectivity:

```json
{
  "status": "ok",
  "database": { "dialect": "postgresql", "status": "ok" }
}
```
