# BC/CP Rights Mechanism v0.1

This document defines the small rights engine used by the PoCP backend MVP.

## Terms

- **BC v0.1**: Benefit Credits, implemented as the existing `Wallet.ai_credits`
  balance and `CreditType.ai_credits` transactions. BC is spendable on protocol
  AI services.
- **CP v0.1**: Contribution Proof, implemented as the existing
  `Wallet.cp_balance` balance and `CreditType.cp` transactions. CP is
  non-spendable proof of approved contribution.

The current code keeps the database schema stable and formalizes semantics in
`backend/services/rights.py`.

## Policy

Rights policy lives in `backend/config/pocp_rewards.yaml` under `rights`:

- `rights.bc.spendable: true`
- `rights.bc.transferable: false`
- `rights.cp.spendable: false`
- `rights.cp.transferable: false`

Defaults are mirrored in `backend/services/protocol_config.py` so the service
has deterministic behavior if the YAML file is unavailable.

## Issuance

Registration grants mint BC only for human entities.

Approved human contribution mints both:

- CP v0.1 as non-spendable contribution proof.
- BC v0.1 as spendable AI Credits.

Only human `creator` and `executor` participants receive BC/CP rights in v0.1.
Skill and agent participants continue to receive reputation rather than wallet
rights.

## Spending

BC spending remains the existing AI Credits burn path. CP has no spend API.
`services.rights.assert_spendable("cp")` raises an error by policy, making CP
explicitly non-spendable for future integrations.

## Ledger

Rights grants are included in ledger payloads with:

- `kind`: `bc` or `cp`
- `version`: `bc_v0_1` or `cp_v0_1`
- `amount`
- `spendable`
- `transferable`

This keeps v0.1 rights auditable without adding new tables or migrations.
