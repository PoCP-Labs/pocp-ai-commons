# PoCP AI Commons — Backend

FastAPI service implementing **PoCP Protocol Spec V0.1** (entity-centric model).

## Run locally

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

On first start, the API:

1. Creates SQLite DB at `backend/data/pocp.db`
2. Upserts genesis LLM entities **Lumen-0** (witness) and **DeSui** (validator) on every startup
3. Seeds the **R Language Study Materials** demo (Alice, Bob, StudyAgent, R-Tutor Skill, PoCP AI Commons org)
4. Runs one full loop: submit → dual AI verify (Lumen-0 + DeSui) → human approve → ledger

Reset demo data:

```bash
python scripts/reset_db.py
# then restart uvicorn or docker compose
```

Existing databases gain DeSui on restart; full demo re-seed requires reset.

## Docker

From repository root:

```bash
docker compose up backend
```

## API

- Health: `GET /health`
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
