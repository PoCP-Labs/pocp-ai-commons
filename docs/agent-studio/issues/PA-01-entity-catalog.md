# [PA-1] Entity catalog — register all 14 types + capability registry

**Labels:** `phase-a`, `entity-ontology`, `capability-registry`, `agent-studio`  
**Meta Agents:** Atlas-0 (schema), Pulse-0 (registry), Grid-0 (compute_node link)  
**Mission plan handoff:** `phase_a_kernel` → Atlas-0, Pulse-0

## Problem

Live Postgres had 73 entities but **missing ontology types**: `compute_node`, `verifier_node`, `reviewer_node`, `sponsor`, `protocol_treasury`. Capability registry returned **count: 0**.

## Expected output

- [x] `backend/services/entity_catalog.py` — `ensure_platform_entity_catalog()`, `audit_entity_catalog()`
- [x] `backend/scripts/audit_entities.py` — `--repair` against Postgres (loads `.env`)
- [x] `seed.py` calls catalog on startup (early-return + full seed paths)
- [ ] Commit WIP files; PR with tests green
- [ ] Wire `entity_catalog` acceptance into `run_phase_a_acceptance.py` (see PA-5)
- [ ] `GET /api/v1/registry/capabilities` returns ≥ 11 entries on `:8008`

## Stable entity IDs

| Type | ID |
|------|-----|
| compute_node | `pocp-entity-local-compute` |
| verifier_node | `pocp-entity-local-verifier` |
| reviewer_node | `pocp-entity-bob-reviewer` |
| sponsor | `pocp-entity-rain-sponsor` |
| protocol_treasury | `pocp-entity-protocol-treasury` |
| workflow (demo) | `pocp-entity-study-workflow` |

## Acceptance

```powershell
python backend/scripts/audit_entities.py --repair
# Complete: True; missing_types: []
python -m pytest backend/tests/test_entity_catalog.py -q
```

## Files

- `backend/services/entity_catalog.py`
- `backend/scripts/audit_entities.py`
- `backend/services/entity_register.py` (`register_workflow` entity_id)
- `backend/seed.py`
- `backend/tests/test_entity_catalog.py`

## Notes

Host scripts must load `backend/.env` — default sqlite fallback is **not** the Docker Postgres volume.
