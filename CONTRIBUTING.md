# Contributing to PoCP AI Commons

Welcome! PoCP AI Commons is the first open-source application of the **Proof of Contribution Protocol (PoCP)** — a protocol that lets ordinary people earn AI access through verified contribution.

Every genuine contribution is welcome. Here's how to get started.

## Quick Start

### Prerequisites

- **Python 3.11+**
- **Docker & Docker Compose** (recommended)
- **Node.js 18+** (for frontend)

### Local Development

```bash
# Start everything with Docker Compose
docker compose up --build

# Backend will be at http://localhost:8000
# API docs at http://localhost:8000/docs
# Frontend at http://localhost:3000
```

### Manual Setup

```bash
# Backend
cd backend
pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev
```

### Smoke Test

After the backend is running, verify the full loop:

```bash
cd backend
python scripts/smoke_test.py
```

This seeds a demo scenario and completes one full `submit → AI verify → human approve` loop.

## Project Structure

```
├── backend/
│   ├── main.py                 # FastAPI app entry
│   ├── database.py             # SQLAlchemy setup
│   ├── models/                 # SQLAlchemy models
│   │   ├── entity.py           # Entity (Human, Agent, Skill, etc.)
│   │   ├── task.py             # Contribution tasks
│   │   ├── contribution.py     # Contribution events & reviews
│   │   ├── wallet.py           # AI Credits, CP, ledger
│   │   ├── ledger.py           # Append-only audit log
│   │   ├── invocation.py       # Agent/Skill invocation traces
│   │   ├── agent.py            # Agent entity extension
│   │   ├── skill.py            # Skill entity extension
│   │   └── organization.py     # Organization entity extension
│   ├── schemas/                # Pydantic request/response schemas
│   ├── routers/
│   │   └── api.py              # All API endpoints
│   ├── services/
│   │   ├── contribution.py     # Approval & reward logic
│   │   ├── graph.py            # Contribution graph builder
│   │   └── invocation.py       # Invocation recording
│   ├── scripts/
│   │   └── smoke_test.py       # End-to-end smoke test
│   └── seed.py                 # Demo seed data
├── frontend/                   # React + Vite dashboard
├── docs/                       # Extended documentation
├── GENESIS.md                  # Why PoCP exists
├── AI-COMMONS.md               # AI Commons concept
└── PROTOCOL-SPEC-v0.1.md       # Builder-facing protocol spec
```

## The Core Loop

PoCP AI Commons proves one loop:

```
Entity registers → receives starter AI Credits
→ completes task → submits contribution
→ AI advisory verify → human approve
→ CP + AI Credits issued → ledger written
```

Understanding this loop is the key to understanding the codebase.

## What We Need Help With

### 🟢 Good First Issues

Look for issues labeled `good first issue`. These are great starting points:

- Documentation improvements
- Small bug fixes
- Test writing
- Frontend UI tweaks

### 🔵 Backend Development

- **API endpoints**: New routes per the protocol spec
- **Models & schemas**: Extending entity types (LLM, Tool, Dataset, etc.)
- **Services**: Business logic for verification, rewards, reputation
- **Tests**: Unit and integration tests (currently minimal)

### 🟡 Frontend Development

- **Dashboard**: Entity management, task browsing
- **Contribution submission flow**: Better UX for submitting evidence
- **Graph visualization**: Contribution relationship explorer
- **Wallet display**: AI Credits and CP balance UI

### 🟠 Documentation

- Protocol explanations
- API tutorials
- Architecture diagrams
- User guides

### 🔴 Protocol Design

- Entity rights model discussions
- Verification rubric design
- Reputation decay mechanisms
- Governance patterns

## How to Contribute

1. **Find or create an issue** — Describe what you want to work on
2. **Fork the repo** and create a branch
3. **Make your changes** — Follow the coding style below
4. **Test** — Run the smoke test, add tests if applicable
5. **Open a PR** — Describe what you changed and why

## Coding Style

- **Python**: Follow PEP 8. Use type hints (the codebase uses SQLAlchemy 2.0 `Mapped` style).
- **FastAPI**: Keep routers thin, push logic to services.
- **Schemas**: All request/response schemas in `backend/schemas/`.
- **Models**: One model per file in `backend/models/`, re-exported via `__init__.py`.
- **Commits**: Write clear commit messages. Reference issue numbers when applicable.

## Testing

```bash
# Run smoke test (end-to-end demo loop)
cd backend && python scripts/smoke_test.py

# Run unit tests (when available)
cd backend && python -m pytest tests/
```

## API Development

New endpoints should:

1. Follow the RESTful pattern in `backend/routers/api.py`
2. Use Pydantic schemas from `backend/schemas/`
3. Return proper HTTP status codes (201 for creation, 400 for bad request, 404 for not found)
4. Use `HTTPException` with descriptive `detail` messages

## Protocol Changes

Changes to the core protocol (entity rights, verification rules, reward formulas) require:

- A PR with clear rationale
- Discussion in the related issue
- Maintainer consensus for constitutional changes

See [PROTOCOL-SPEC-v0.1.md](./PROTOCOL-SPEC-v0.1.md) for the current spec.

## Questions?

- Open an issue for discussions
- Check existing docs in `docs/`
- Read [GENESIS.md](./GENESIS.md) for the project's vision

---

*Contribution is the proof. AI access is the right.*
