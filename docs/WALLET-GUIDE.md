# Wallet Guide — CP & AI Credits

PoCP wallets hold **two assets** with different roles. All balance changes flow through `credit_transactions` (Bitcoin-inspired: transactions are truth, balances are derived state).

See also: [AI-CREDITS-GUIDE.md](./AI-CREDITS-GUIDE.md) · [API-SPEC.md](./API-SPEC.md) · [COMPUTE-BALANCE-SPEC.md](./COMPUTE-BALANCE-SPEC.md)

---

## Assets

| Asset | Field | Spendable | Purpose |
|-------|--------|-----------|---------|
| **CP** | `cp_balance` | No (v0.1) | Contribution proof — portable reputation signal |
| **AI Credits (BC)** | `ai_credits` | Yes | Protocol usage rights — AI Chat, compute consumer, etc. |

Issuance is capped by daily budget (`GET /api/v1/issuance/budget`). Operator cannot silently mint — balances must replay from transactions (`GET /api/v1/wallets/audit`).

---

## Default flows

```text
Register (Human) → registration_grant → +100 BC (typical)
Contribute → finalize → +CP + BC (human creator/executor)
AI Chat → ai_credits_burned → -5 BC per message (configurable)
Compute consume → compute_consumed → -BC consumer
Compute provide → compute_provided / intel_provided → +BC provider
```

Entity-equal policy may issue BC to Agent / Skill / LLM participants on approved contributions.

---

## Authenticated API (`Bearer` token)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/wallets/me/summary` | Balances, today earn/spend, compute totals, audit flag |
| GET | `/api/v1/wallets/me/transactions` | Paginated history with `category`, `ledger_link` |
| POST | `/api/v1/wallets/me/quote` | Pre-flight cost (`{"action":"ai_chat"}`) |
| GET | `/api/v1/wallets/me/export` | Downloadable audit bundle |
| POST | `/api/v1/wallets/me/export/verify` | Verify an export JSON (replay balances) |

Query params for transactions: `limit`, `offset`, `credit_type=cp|ai_credits`.

---

## Public read (any Entity)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/wallets/{entity_id}/summary` | Entity profile wallet stats |
| GET | `/api/v1/wallets/{entity_id}/transactions` | Recent activity |
| GET | `/api/v1/wallets/{entity_id}/audit` | Transaction replay audit |

---

## Ledger linkage

Each transaction may include `ledger_link`:

```json
{
  "ledger_record_id": "...",
  "ledger_event_type": "contribution_approved",
  "ledger_record_hash": "..."
}
```

Links are resolved heuristically (contribution + time window + payload). Future versions may store `ledger_record_id` on `credit_transactions` directly.

---

## Frontend

- **Wallet** tab — balances, filters, export, ledger/proof navigation
- **AI Node** — quote-driven send button; insufficient balance blocked early
- **Entity detail** — `EntityWalletActivity` recent transactions

---

## Offline audit

```bash
# Export (authenticated)
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/wallets/me/export -o wallet.json

# Verify replay
curl -X POST http://localhost:8000/api/v1/wallets/me/export/verify \
  -H "Content-Type: application/json" -d @wallet.json

# Node-wide audit (operator)
curl http://localhost:8000/api/v1/wallets/audit
python backend/scripts/audit_node.py remote --url http://127.0.0.1:8000
```

---

## Configuration

- `backend/config/pocp_rewards.yaml` — registration grant, contribution defaults, entity-equal BC
- `AI_CHAT_COST_PER_MESSAGE` — quote + burn amount
- `issuance_budget` — daily CP/BC caps

---

## Smoke test

```bash
python backend/scripts/smoke_test.py http://127.0.0.1:8000
```

Includes wallet quote, summary, transactions, and export verify after AI chat.
