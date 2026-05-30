# PoCP AI Commons

**Earn AI access through verified contribution.**

PoCP AI Commons is the first open-source application of the **Proof of Contribution Protocol (PoCP)**.

It is designed to explore a new question for the age of AI:

> If AI becomes a basic productive capability, how can ordinary people gain fair access to it through real contribution?

---

## Core Idea

```text
User pays → User uses AI        ← Most platforms

User contributes                ← PoCP AI Commons
  ↓
Contribution is verified
  ↓
User earns CP and AI Credits
  ↓
User uses AI
  ↓
AI helps user contribute more
```

---

## Quick Start

### Prerequisites

- **Python 3.11+**
- **Docker & Docker Compose** (recommended)

### Docker

```bash
docker compose up --build
```

Backend: http://localhost:8000 | API docs: http://localhost:8000/docs | Frontend: http://localhost:3000

### Manual

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Smoke Test

```bash
cd backend
python scripts/smoke_test.py
```

---

## Architecture

```
┌──────────────┐
│   Frontend    │  React + Vite SPA
│  (localhost)  │
└──────┬───────┘
       │
┌──────▼───────┐
│   Backend     │  FastAPI (modular routers)
│  port 8000    │
└──────┬───────┘
       │
┌──────▼───────┐
│   SQLite      │  (PostgreSQL ready via Alembic)
│  pocp.db      │
└──────────────┘
```

### Backend Structure

```
backend/
├── main.py                  # App entry + middleware + error handlers
├── config.py                # Centralized configuration (env vars)
├── database.py              # SQLAlchemy setup
├── alembic/                 # Database migrations
├── models/                  # SQLAlchemy models (Entity, Task, Contribution, etc.)
├── schemas/                 # Pydantic request/response schemas
├── routers/                 # Modular API routers
│   ├── api.py              # Aggregates all sub-routers
│   ├── auth.py             # POST /auth/token
│   ├── entities.py         # Entity CRUD + filters
│   ├── tasks.py            # Task CRUD + GET /{id}
│   ├── contributions.py    # Submit / Verify / Approve / Reject
│   ├── wallets.py          # Wallets / Ledger / Reputation
│   ├── skills.py           # Skills / Agents
│   ├── organizations.py    # Organization management
│   ├── invocations.py      # Invocation traces
│   └── graph.py            # Contribution graph
├── services/                # Business logic
│   ├── auth.py             # JWT auth framework
│   ├── contribution.py     # Approval + rewards
│   ├── rejection.py        # Rejection with audit trail
│   ├── entities.py         # Entity management
│   ├── graph.py            # Graph builder
│   ├── invocation.py       # Invocation recording
│   └── migrations.py       # Auto-migration on startup
├── middleware/              # HTTP middleware
│   ├── request_id.py       # X-Request-ID correlation
│   └── rate_limit.py       # Per-IP rate limiting
├── tests/                   # Unit + integration tests
│   ├── conftest.py         # Test fixtures
│   ├── test_api.py         # API integration tests
│   ├── test_auth.py        # Auth + edge case tests
│   ├── test_contribution.py # Contribution logic tests
│   ├── test_protocol.py    # Protocol property tests
│   └── test_rejection.py   # Rejection tests
└── scripts/
    └── smoke_test.py        # End-to-end smoke test
```

---

## The Core Loop

```text
Entity registers → receives starter AI Credits
  → completes task → submits contribution
  → AI advisory verify → human approve
  → CP + AI Credits issued → ledger written
```

---

## What Is PoCP?

**PoCP** (Proof of Contribution Protocol) records and verifies contributions from humans, AI agents, skills, tools, datasets, workflows, organizations, and communities.

PoCP does not ask only: *Who owns what?*

It asks:
- *Who contributed what?*
- *Who verified it?*
- *Who benefited from it?*
- *What rights should follow from it?*

See [PROTOCOL-SPEC-v0.2.md](./PROTOCOL-SPEC-v0.2.md) for the full protocol definition.

---

## AI Is a Witness, Not a Ruler

AI verifiers assist in contribution review but **cannot make the final decision**. Final approval must always come from human reviewers.

---

## Key Files

| File | Purpose |
|------|---------|
| [PROTOCOL-SPEC-v0.2.md](./PROTOCOL-SPEC-v0.2.md) | Builder-facing protocol contract |
| [GENESIS.md](./GENESIS.md) | Why PoCP exists — the vision |
| [AI-COMMONS.md](./AI-COMMONS.md) | First application concept |
| [CONTRIBUTING.md](./CONTRIBUTING.md) | How to contribute |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | Architecture review and roadmap |
| [docs/](./docs/) | Extended documentation |

---

## Environment Variables

Copy `backend/.env.example` to `backend/.env`:

```bash
cp backend/.env.example backend/.env
```

Key variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:///data/pocp.db` | Database connection string |
| `AUTH_MODE` | `demo` | `demo` (no auth) or `jwt` (token required) |
| `JWT_SECRET` | `change-me-in-production` | Secret key for JWT tokens |
| `CORS_ORIGINS` | `*` | Comma-separated allowed origins |
| `RATE_LIMIT` | `100` | Max requests per minute per IP |
| `LOG_LEVEL` | `INFO` | Logging level |
| `SEED_ON_STARTUP` | `true` | Whether to seed demo data |

---

## Contributing

We welcome contributions! See [CONTRIBUTING.md](./CONTRIBUTING.md) for a guide.

---

## License

MIT — see [LICENSE](./LICENSE).

---

*Contribution is the proof. AI access is the right.*
