# API Spec — Sprint Alpha

Base URL: `http://localhost:8000` (development)

Interactive docs: `/docs` · Health: `/health`

## Auth

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/auth/github/login` | Redirect to GitHub OAuth |
| GET | `/api/v1/auth/github/callback` | OAuth callback → redirect to frontend with JWT |
| POST | `/api/v1/auth/dev-login` | Local dev login; creates Human Entity + Wallet |
| GET | `/api/v1/me` | Current user, entity, wallet (Bearer token) |
| POST | `/api/v1/auth/logout` | Logout ack |

**Dev login body:**

```json
{ "username": "rain", "email": "rain@example.com" }
```

## AI Chat & Credits

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/ai/chat` | Send message; burns AI Credits (default 5) |
| GET | `/api/v1/ai/usage` | AI usage log for current user |

**Chat body:**

```json
{ "message": "Explain contribution events", "provider": "mock" }
```

Providers: `mock`, `openai`, `deepseek` (when API keys configured).

## Entities & tasks

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/entities` | List entities |
| GET | `/api/v1/tasks` | List tasks |
| POST | `/api/v1/tasks` | Create task (authorized sponsor) |

## Contributions

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/contributions` | List contributions |
| POST | `/api/v1/contributions` | Submit contribution (evidence required) |
| POST | `/api/v1/contributions/{id}/auto-verify` | Run multi-verifier AI review (advisory) |
| POST | `/api/v1/contributions/{id}/approve` | Human final approval |
| GET | `/api/v1/contributions/{id}/clarion-review` | Clarion-0 reviewer assistant packet |
| GET | `/api/v1/contributions/{id}/proof` | Contribution Proof Packet |

## Verification

Manual verify endpoint exists but is disabled by default; use `auto-verify`.

## Wallet, reputation, ledger, graph

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/wallets` | All wallets |
| GET | `/api/v1/reputation` | Reputation records |
| GET | `/api/v1/ledger` | Ledger records |
| GET | `/api/v1/ledger/verify` | Verify hash chain integrity |
| GET | `/api/v1/ledger/export` | Export ledger |
| GET | `/api/v1/graph` | Contribution graph nodes + edges |
| GET | `/api/v1/invocations` | Invocation chains |

## Portable & federation

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/entities/{id}/portable` | Portable entity export |
| GET | `/api/v1/federation/node` | Node metadata |
| POST | `/api/v1/federation/import-proof` | Import proof from trusted node |
| GET | `/api/v1/federation/imports` | List imports |

## Auth header

```http
Authorization: Bearer <access_token>
```

## Error semantics

- `401` — missing/invalid token
- `403` — anti-abuse or permission (e.g. self-approval, unauthorized task)
- `400` — validation (missing evidence, insufficient credits)

## Related docs

- [Sprint Alpha](./SPRINT_ALPHA.md)
- [AI Credits Guide](./AI-CREDITS-GUIDE.md)
- [Verifier Guide](./VERIFIER-GUIDE.md)
- [Human Review Guide](./HUMAN-REVIEW-GUIDE.md)
