# Token Measurement Schema v0.3

## Units

```text
CP  = Contribution Points
AIC = AI Credits
CC  = Compute Credits
PT  = PoCP Protocol Token internal account
```

All units are **internal accounting** at this stage. Tokenized measurement does not mean public token issuance ([NO-TOKEN-FIRST.md](../../NO-TOKEN-FIRST.md)).

## Wallet mapping

| Unit | Wallet / account field | Runtime |
|------|------------------------|---------|
| CP | `cp_balance` | `CreditType.cp` |
| AIC | `ai_credits` | `CreditType.ai_credits`; compute metering debits this column |
| CC | `compute_credit_balance` | CIP `TokenAccountData` (future wallet column) |
| PT | `pocp_token_balance_internal` | Internal-only; unified metering may alias to AIC when enabled |

## Token Account

```json
{
  "account_id": "acct_001",
  "entity_id": "entity_001",
  "cp_balance": 0,
  "ai_credit_balance": 0,
  "compute_credit_balance": 0,
  "pocp_token_balance_internal": 0,
  "locked_balance": 0,
  "staked_balance": 0,
  "pending_rewards": 0
}
```

## Audit (CI-12)

Prism-0 exposes `services.token_measurement.audit_protocol_economy()` — validates unit consistency, settlement policy YAML, and Lex NO-TOKEN-FIRST guard on protocol economy docs.

```bash
cd backend && python -m pytest tests/ -k settlement_policy -q
```
