# Settlement Spec

Settlement defines who receives what after verified contribution or invocation.

## Policy file

Versioned policies live in `backend/config/settlement_policies.yaml` (canonical). Agent Studio CI-12 references this file as `settlement_policy.yaml`; the loader accepts either path.

Loaded by `services/settlement_policy.py` and tagged on `exchange_settled` ledger payloads (`settlement_policy_id`, `settlement_policy_version`, `policy_hash`).

## Internal units (NO-TOKEN-FIRST)

Settlement uses internal accounting units only — see [TOKEN-MEASUREMENT-SCHEMA-v0.3.md](./TOKEN-MEASUREMENT-SCHEMA-v0.3.md) and [NO-TOKEN-FIRST.md](../../NO-TOKEN-FIRST.md):

```text
CP  = Contribution Points (internal)
AIC = AI Credits (internal usage rights)
CC  = Compute Credits (internal)
PT  = PoCP internal account — not publicly exchange-listed
```

Policy YAML must keep `no_public_token_guard.enabled: true`. Lex-0 reviews user-facing copy; Prism-0 runs `audit_protocol_economy()` in CI.

## Flow (target)

Current `approve_contribution` logic should later be refactored into:

```text
create_settlement()
→ apply_settlement()
→ write_ledger()
→ update_reputation()
```

Do not rewrite the existing contribution service in this patch.

## Offline replay

`replay_bilateral_quote()` and `replay_flat_debit_quote()` recompute expected debits/credits from receipts without mutating wallets — used for dispute replay and CI verification.
