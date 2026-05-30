# PoCP AI Commons — Architecture Review & Roadmap

> Authored by Proof 🧬 — May 30, 2026

## Current Architecture

```
Frontend (React SPA) → Backend (FastAPI) → SQLite (local file)
```

**Status:** Early MVP (v0.1-Genesis). Core loop works:
`register → task → contribute → AI verify → human approve → CP + Credits → ledger`

---

## Problem Assessment

### 🔴 Critical (Fix Now)

| # | Issue | Impact |
|---|---|---|
| 1 | **Zero authentication** | Anyone can approve any contribution with a fake `reviewer_id` |
| 2 | **No database migrations** | Model changes break existing data |
| 3 | **Monolithic `api.py` (13KB)** | Hard to maintain, test, or review |
| 4 | **No pagination** | List endpoints load entire tables into memory |
| 5 | **Seed blocks startup** | Service won't start if seed fails |
| 6 | **No error handling** | Internal errors exposed as 500 with stack traces |
| 7 | **CORS `*` in production** | Security risk |

### 🟡 Important (Fix Soon)

| # | Issue | Impact |
|---|---|---|
| 8 | SQLite concurrent write locks | Blocks under multi-user load |
| 9 | No structured logging | Can't debug production issues |
| 10 | Hardcoded reward formulas | Can't adjust CP/Credits without code change |
| 11 | No rate limiting | API vulnerable to abuse |
| 12 | `--reload` in Dockerfile | Production shouldn't use dev mode |

### 🟢 Future (Plan Ahead)

| # | Issue | Impact |
|---|---|---|
| 13 | Sync AI verification | Blocks on LLM API calls |
| 14 | No webhook/callback system | Can't notify contributors on approval |
| 15 | No export (CSV/JSON) | Can't analyze contribution data externally |
| 16 | Frontend single-file | Needs component architecture |

---

## Target Architecture (v0.3)

```
┌─────────────────────────────────────────────────────────┐
│                     Frontend (SPA)                       │
│  React + Vite + Component Architecture + PWA             │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTPS
┌──────────────────────▼──────────────────────────────────┐
│                   Reverse Proxy                          │
│  Nginx/Traefik: SSL termination, rate limit, CORS       │
└──────────┬──────────────┬──────────────┬────────────────┘
           │              │              │
    ┌──────▼──────┐ ┌────▼─────┐ ┌──────▼──────┐
    │  Auth Layer  │ │ API GW   │ │  Webhook    │
    │  (GitHub     │ │ (FastAPI │ │  Service    │
    │   OAuth)     │ │  modular)│ │             │
    └──────────────┘ └────┬─────┘ └─────────────┘
                          │
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
    ┌───────────┐  ┌───────────┐  ┌──────────────┐
    │ PostgreSQL│  │   Redis   │  │  Background   │
    │ (Alembic) │  │ (cache,   │  │  Workers      │
    │           │  │  queue)   │  │  (Celery/ARQ) │
    └───────────┘  └───────────┘  └──────┬───────┘
                                         │
                                  ┌──────▼───────┐
                                  │ AI Verifiers │
                                  │ (async LLM)  │
                                  └──────────────┘
```

---

## Implementation Phases

### Phase 1: Foundation (Completed ✅)
- [x] CONTRIBUTING.md — contributor guide
- [x] Missing API endpoints (GET /tasks/{id}, GET /wallets/{id}, POST /reject)
- [x] Unit tests (12 tests)
- [x] GitHub Actions CI
- [x] Router modularization
- [x] Pagination on all list endpoints
- [x] Error handling middleware
- [x] CORS environment variable
- [x] Alembic migration setup
- [x] Non-blocking seed on startup

### Phase 2: Security (Next)
- [ ] GitHub OAuth authentication
- [ ] JWT token management
- [ ] RBAC (Role-Based Access Control)
  - Only task sponsors and designated reviewers can approve
  - Self-approval prevention (already exists)
  - Entity-level permissions
- [ ] Request signing / replay protection
- [ ] Rate limiting (per-entity, per-IP)

### Phase 3: Scalability
- [ ] PostgreSQL migration
- [ ] Redis caching for:
  - Entity lookups
  - Graph computation
  - Wallet balances
- [ ] Background task queue (Celery/ARQ):
  - Async AI verification
  - Ledger writes
  - Notification dispatch
- [ ] Health checks and readiness probes

### Phase 4: AI Integration
- [ ] Real LLM verifier integration:
  - DeepSeek API
  - OpenAI API
  - Local model support (Ollama)
- [ ] Multi-model consensus verification
- [ ] Verification rubric configuration
- [ ] AI Credits spending (chat, tool usage)

### Phase 5: Governance
- [ ] Reputation decay mechanism
- [ ] Community voting on disputed contributions
- [ ] Task sponsorship by organizations
- [ ] Contribution graph explorer UI
- [ ] Export (CSV, JSON-LD)

---

## Key Design Decisions

### Why Modular Routers?
Single `api.py` with 350+ lines and all endpoints violates:
- Single Responsibility Principle
- Testability (can't test routes in isolation)
- Code review efficiency

Splitting by resource (entities, tasks, contributions, etc.) allows parallel development.

### Why Alembic?
`Base.metadata.create_all()` can only create tables, never modify them.
Alembic provides:
- Versioned migrations
- Upgrade/downgrade paths
- Schema documentation

### Why Pagination?
`db.query().all()` loads entire tables into memory. At 10K contributions,
this becomes a memory and latency problem. Pagination is a basic API hygiene practice.

### Why Error Handlers?
Without exception handlers, SQLAlchemy errors leak internal details as 500 responses.
Structured error responses (409 Conflict, 422 Validation, 503 Service Unavailable)
help frontend developers and API consumers.

---

## Metrics to Track

| Metric | Current | Target |
|--------|---------|--------|
| API endpoints | 16 | 20+ |
| Test coverage | ~15% | 80%+ |
| Avg response time | ~50ms | <200ms at p95 |
| Concurrent users | 1 (demo) | 100+ |
| API error rate | Unknown | <1% |

---

*Contribution is the proof. AI access is the right.*
