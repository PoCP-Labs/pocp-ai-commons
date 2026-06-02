# [PA-4] Federation acceptance — full green on :8100 / :8101

**Labels:** `phase-a`, `federation`, `acceptance`  
**Meta Agents:** Mesh-0, Gauge-0  
**Mission plan handoff:** `phase_a_kernel` → Mesh-0 → Gauge-0

## Problem

Single-node `:8008` lacks federation crypto keys and peer compute — **do not** run federation acceptance there. Node A/B on `:8100`/`:8101` were last **almost PASS**; `invocation_ref_integrity` failed (404) likely due to stale containers.

## Acceptance criteria

- [ ] `docker compose -f docker-compose.federation.yml` backends restarted after PR-A/B code
- [ ] `run_phase_a_acceptance.py` **all steps PASS** including:
  - `peer_witness_verify`
  - `invocation_ref_integrity`
  - `exchange_proof_demo`
  - `wallet_audit`
  - `federation_exchange_demo`
- [ ] Gauge-0 outcome recorded: `acceptance` / `pass`

## Commands

```powershell
docker compose -f docker-compose.federation.yml restart backend-a backend-b
python backend/scripts/run_phase_a_acceptance.py http://127.0.0.1:8100 --federation http://127.0.0.1:8101
cd backend && python -m pytest -q
```

## Do not

- Run federation acceptance against `http://127.0.0.1:8008`
- Deploy public staging (deferred by product decision)
