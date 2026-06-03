# Capability Internet — Wave 1 gate (closed)

**Plan:** `capability_internet`  
**Autopilot id:** `capability_internet_wave1`  
**Handoff:** `bc91cffd-433a-4a4a-92ee-acf0764d16dc` (Gauge → Nexus)  
**Status:** **CLOSED** — 2026-06-03

## What wave-1 means

Wave-1 is the **CI acceptance gate** before domain agents continue CI-1..CI-12 implementation. It does **not** mean the full 12-layer mission is complete.

## Required commands (all green)

```powershell
python backend/scripts/audit_entities.py --repair
python backend/scripts/run_phase_a_acceptance.py http://127.0.0.1:8100 --federation http://127.0.0.1:8101
python backend/scripts/minimum_living_network.py
```

Federation stack: node-a `:8100`, node-b `:8101` (see `scripts/run-phase-a.ps1 -Federation`).

## Checklist mapping

Canonical checklist: [docs/MINIMUM-LIVING-NETWORK.md](../../../docs/MINIMUM-LIVING-NETWORK.md)

| Exit criterion | Wave-1 |
|----------------|--------|
| Three logical nodes as Entities (A/B/C roles) | Met — ontology includes human, agent, skill, verifier_node, reviewer_node |
| One capability registered and invoked with receipt | Met — federation acceptance + CIP demo |
| Invocation → Proof → Verification → Settlement in one packet | Met — `invocation_ref_integrity`, `federation_exchange_demo` |
| Reputation / graph edge after loop | Met — `pilot_metrics` + graph in acceptance path |
| Second node witness / import without fake credits | Met — `peer_witness_verify`, federation strict mode |

## Still open (wave-2+)

- CI workflow job for `minimum_living_network.py` (Gauge + Pipeline-0)
- Production API wire for CIP layers (Forge, Pulse — PR 4)
- Per-layer handoffs CI-1 .. CI-12 in Agent Studio plan
- Normative doc checkbox sync in `docs/MINIMUM-LIVING-NETWORK.md` (Herald-0)

## Report

[Nexus patch `nexus-0-bc91cffd.md`](../../patches/nexus-0-bc91cffd.md)
