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
| GET | `/api/v1/entities/ontology` | Canonical Entity type × role ontology |
| GET | `/api/v1/entities/{id}/ontology` | Ontology slice for one entity |
| POST | `/api/v1/entities/tool` | Register Tool entity (auth required) |
| POST | `/api/v1/entities/dataset` | Register Dataset entity (auth required) |
| POST | `/api/v1/entities/workflow` | Register Workflow entity (auth required) |
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
| GET | `/api/v1/wallets/me/summary` | Authenticated wallet summary (Bearer) |
| GET | `/api/v1/wallets/me/transactions` | Transaction history with ledger links |
| POST | `/api/v1/wallets/me/quote` | Pre-flight spend quote (`ai_chat`, etc.) |
| GET | `/api/v1/wallets/me/export` | Personal wallet audit bundle |
| POST | `/api/v1/wallets/me/export/verify` | Verify export JSON replay |
| GET | `/api/v1/wallets/{entity_id}/summary` | Public entity wallet summary |
| GET | `/api/v1/wallets/{entity_id}/transactions` | Public entity transactions |
| GET | `/api/v1/wallets/audit` | Recompute all balances from transactions |
| GET | `/api/v1/wallets/export` | Operator full wallet export |
| POST | `/api/v1/wallets/export/verify` | Verify operator export |
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

## Intelligence Capability Layer

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/intelligence/protocol` | Unified contribution protocol descriptor |
| GET | `/api/v1/intelligence/status` | Capability module registry |
| GET | `/api/v1/intelligence/entities/{id}/profile` | Entity wallet, reputation, contribution stats |
| POST | `/api/v1/intelligence/entities/register` | Register contribution-capable entity (Tool, Dataset, etc.) |
| GET | `/api/v1/intelligence/contributions/{id}/packet` | Full advisory intelligence packet |
| GET | `/api/v1/intelligence/federation/export/{contribution_id}` | Cross-node intelligence + proof bundle |
| POST | `/api/v1/intelligence/federation/ingest-preview` | Advisory summary of received federation packet |
| GET | `/api/v1/intelligence/governance/summary` | Advisory governance snapshot |
| POST | `/api/v1/intelligence/match` | Recommend agents/skills (v0.3 semantic matching, advisory) |

## Crypto Agility / Quantum Readiness

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/crypto/suites` | Registered crypto suites (classic + hybrid) |
| GET | `/api/v1/crypto/readiness` | Node quantum-readiness snapshot |
| GET | `/api/v1/crypto/suites/{suite_id}` | Single suite specification |

See [QUANTUM-READINESS.md](./QUANTUM-READINESS.md).

## Distributed Compute / Intelligence Mesh

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/intelligence/entities/{id}/compute/register` | Register Entity ComputeProfile |
| GET | `/api/v1/compute/providers` | List Entity compute providers |
| POST | `/api/v1/compute/jobs` | Schedule compute job (advisory + receipt) |
| GET | `/api/v1/compute/jobs/{id}` | Job status + ComputeReceipt |
| POST | `/api/v1/compute/entities/{id}/heartbeat` | Provider liveness |

See [ARCHITECTURE.md](./ARCHITECTURE.md) for compute and intelligence modules (experimental APIs).

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
- [Wallet Guide](./WALLET-GUIDE.md)
- [Verifier Guide](./VERIFIER-GUIDE.md)
- [Human Review Guide](./HUMAN-REVIEW-GUIDE.md)
