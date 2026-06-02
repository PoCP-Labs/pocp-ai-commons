# [PA-5] Entity catalog acceptance step

**Labels:** `phase-a`, `entity-ontology`, `acceptance`  
**Meta Agents:** Gauge-0, Pulse-0  
**Mission plan handoff:** `phase_a_kernel` → Gauge-0 (depends on PA-1)

## Problem

Entity catalog repair is manual (`audit_entities.py --repair`); acceptance runner should gate releases on ontology completeness.

## Expected output

- [ ] New step in `run_phase_a_acceptance.py`: `entity_catalog_complete`
- [ ] Calls `audit_entity_catalog` logic or `GET /api/v1/entities/ontology` + capability count
- [ ] Fails if any of 14 types missing or capability registry empty
- [ ] Documented in `docs/ROADMAP-THREE-PHASES.md`

## Acceptance

```powershell
python backend/scripts/run_phase_a_acceptance.py http://127.0.0.1:8008
# entity_catalog_complete: PASS
```

## Files

- `backend/scripts/run_phase_a_acceptance.py`
- `backend/services/entity_catalog.py`
- `docs/ROADMAP-THREE-PHASES.md`
