# Changelog

All notable changes to PoCP AI Commons will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [v0.2] — 2026-05-30

### Added

- **Protocol hardening**: Contribution Event defined as "responsibility-bearing claim" with 8 protocol principles
- **Modular router architecture**: Split monolithic `api.py` into 8 resource routers (entities, tasks, contributions, wallets, skills, organizations, invocations, graph)
- **Pagination support**: All list endpoints support `skip` and `limit` parameters
- **Error handling middleware**: Structured error responses for IntegrityError, OperationalError, ValidationError, ValueError, PermissionError
- **Rate limiting middleware**: Per-IP rate limiting (configurable, default 100/min)
- **Request ID middleware**: `X-Request-ID` correlation tracking on every request
- **Structured logging**: Request logging with duration, status, and request ID
- **Authentication framework**: JWT-based auth with dual mode (`demo`/`jwt`)
- **Auth token endpoint**: `POST /api/v1/auth/token` for entity authentication
- **Centralized configuration**: All env vars in `config.py` with sensible defaults
- **Service layer**: Entity service with validation, wallet management, and filtering
- **Auto-migration**: Alembic migrations run automatically on startup (PostgreSQL); `create_all` for SQLite
- **Database indexes**: 27 new indexes across all tables for query performance
- **Contribution rejection endpoint**: `POST /contributions/{id}/reject` with audit trail
- **Task GET by ID**: `GET /tasks/{id}` endpoint
- **Wallet GET by entity**: `GET /wallets/{entity_id}` endpoint
- **Entity filtering**: `GET /entities?entity_type=&status=` support
- **Enhanced health check**: Database connectivity verification, degraded status reporting
- **Docker production hardening**: Multi-stage build (dev/prod targets), gunicorn for production
- **docker-compose improvements**: SQLite volume persistence, health check, configurable target
- **ContributionEvent protocol properties**: `has_evidence`, `has_participants`, `has_ai_verification`, `has_human_approval`, `is_established`
- **Protocol validation**: `validate_for_submission()` enforces evidence, task, description, participants at endpoint level

### Changed

- **Reward formulas externalized**: CP, AI Credits, and threshold values now configurable via env vars (no more hardcoded values)
- **Alembic env.py**: Uses `config.DATABASE_URL` instead of hardcoded alembic.ini URL
- **ContributionEvent model**: Enhanced with protocol properties and validation methods
- **README.md**: Updated to reflect current modular architecture

### Documentation

- **PROTOCOL-SPEC-v0.2.md**: Full protocol upgrade with bilingual Contribution Event definition
- **ARCHITECTURE.md**: Comprehensive architecture review and 5-phase roadmap
- **CONTRIBUTING.md**: Contributor guide with project structure and coding style
- **.env.example**: Documentation of all environment variables
- **CHANGELOG.md**: This file

### Testing

- **Unit tests**: 8 contribution logic tests, 4 rejection tests, 25+ protocol property tests
- **Integration tests**: 15+ API endpoint tests, 15+ auth/edge case tests
- **Test fixtures**: Reusable fixtures for entities, tasks, agents, skills, db sessions
- **pytest-cov**: Coverage reporting configured

### Removed

- **`--reload` from production Docker**: Production now uses gunicorn with uvicorn workers

### Security

- **Self-approval prevention**: Already existed, now tested
- **Evidence requirement enforcement**: Empty evidence blocks submission
- **Rate limiting**: Prevents API abuse
- **CORS configurable**: No longer hardcoded to `*` in production (via `CORS_ORIGINS` env var)

---

## [v0.1] — 2026-05-29

### Added

- Initial PoCP AI Commons MVP
- SQLite backend with FastAPI
- Entity registry (Human, Agent, Skill, Organization)
- Task CRUD
- Contribution submission with participants
- AI advisory verification endpoint
- Human approval endpoint with rewards
- Wallet + CP + AI Credits
- Registration grant (100 AI Credits for new humans)
- Contribution graph API
- Invocation chain (Human → Agent → Skill → LLM)
- R language study demo seed
- Frontend dashboard + submit workflow + graph view
- Docker Compose setup
- Smoke test script

---

[v0.2]: https://github.com/PoCP-Labs/pocp-ai-commons/compare/b3f8d94...HEAD
[v0.1]: https://github.com/PoCP-Labs/pocp-ai-commons/commits/b3f8d94
