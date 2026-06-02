# [PA-3] Settlement policy + challenge/appeal (PR-B)

**Labels:** `phase-a`, `settlement`, `verification`, `pr-b`  
**Meta Agents:** Forge-0 (disputes), Prism-0 (settlement policy)  
**Mission plan handoff:** `phase_a_kernel` → Forge-0, Prism-0

## Problem

Contributions need challenge/appeal lifecycle; exchanges need settlement policy tags and offline replay quotes.

## Status

**Implemented in working tree** — verify commit status before merge.

## Expected output

- [ ] `backend/config/settlement_policies.yaml`
- [ ] `backend/services/settlement_policy.py`
- [ ] `backend/services/contribution_dispute.py` + migration
- [ ] Endpoints: challenge, appeal, resolve-dispute, settlement-policies/replay
- [ ] `ContributionStatus`: `challenged`, `appealed`
- [ ] Tests: `test_verification_challenge_flow.py`, `test_settlement_policy_replay.py`
- [ ] Full pytest green; commit if uncommitted

## Acceptance

```powershell
cd backend
python -m pytest tests/test_verification_challenge_flow.py tests/test_settlement_policy_replay.py -q
python -m pytest -q
```

## Files

- `backend/services/settlement_policy.py`
- `backend/services/contribution_dispute.py`
- `backend/routers/verification.py`
- `backend/routers/exchanges.py`
- `backend/alembic/versions/k3l4m5n6o7p8_contribution_disputes.py`
