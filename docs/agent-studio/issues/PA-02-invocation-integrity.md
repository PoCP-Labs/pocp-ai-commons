# [PA-2] Invocation ref integrity (PR-A)

**Labels:** `phase-a`, `protocol-integrity`, `pr-a`  
**Meta Agent:** Vault-0  
**Mission plan handoff:** `phase_a_kernel` → Vault-0

## Problem

Exchange and contribution proofs must carry normalized `invocation_ref` and `invocation_chain_digest` for auditability.

## Status

**Implemented** (commit `2b7a98d` per branch history). Federation acceptance may still **404** on integrity route if `:8100` containers were not restarted after merge.

## Acceptance criteria

- [x] `backend/services/invocation_ledger.py` normalizes invocation refs
- [x] `exchange_settled` rows include `invocation_ref`
- [x] `GET /api/v1/exchanges/{exchange_id}/integrity`
- [x] `backend/tests/test_invocation_ledger_normalization.py`
- [ ] `invocation_ref_integrity` step PASS on `:8100` federation acceptance

## Verification

```powershell
docker compose -f docker-compose.federation.yml restart backend-a backend-b
python backend/scripts/run_phase_a_acceptance.py http://127.0.0.1:8100 --federation http://127.0.0.1:8101
# Step invocation_ref_integrity: PASS
```

## Files

- `backend/services/invocation_ledger.py`
- `backend/routers/exchanges.py`
- `backend/scripts/run_phase_a_acceptance.py`
