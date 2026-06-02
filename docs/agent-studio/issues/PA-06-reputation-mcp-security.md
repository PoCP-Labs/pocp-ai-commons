# [PA-6] Reputation event-sourcing + MCP security baseline (PR-C)

**Labels:** `phase-b-prep`, `reputation`, `mcp`, `security`, `pr-c`  
**Meta Agents:** Sentinel-0, Atlas-0, Pulse-0  
**Mission plan handoff:** `phase_a_kernel` → Sentinel-0 (backlog — after PA-4 green)

## Problem

Phase A kernel complete unlocks PR-C: reputation as event-sourced ledger, MCP invoke security baseline, anti-abuse rules.

## Scope (initial)

- [ ] Reputation events model + append-only store (no commercial ranking optimizer)
- [ ] MCP capability invoke: auth scope, rate limits, receipt logging
- [ ] Anti-abuse policy hooks aligned with `docs/` governance specs
- [ ] Tests + acceptance stub (extend `run_phase_a_acceptance.py` optional section)

## Out of scope

- Public staging deploy
- Token-first messaging / commercial optimizer

## References

- `docs/architecture/08-REPUTATION-GOVERNANCE.md`
- `backend/services/neural/rule_based_router.py`
- `.github/ISSUE_TEMPLATE/reputation_governance_task.md`

## Acceptance (draft)

```powershell
python -m pytest backend/tests/test_reputation_events.py -q  # after added
python backend/scripts/run_phase_a_acceptance.py http://127.0.0.1:8100 --skip-optional
```
