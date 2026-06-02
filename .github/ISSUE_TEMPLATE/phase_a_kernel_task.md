---
name: Phase A Kernel Task
about: Entity catalog, PR-A/B integrity, federation acceptance — Agent Studio PA track
title: "[PA-Kernel] "
labels: "phase-a, agent-studio, kernel"
assignees: ""
---

## PA track item

Link to backlog: [docs/agent-studio/PHASE-A-KERNEL-BACKLOG.md](../../docs/agent-studio/PHASE-A-KERNEL-BACKLOG.md)

| PA | Issue doc |
|----|-----------|
| PA-1 | [PA-01-entity-catalog.md](../../docs/agent-studio/issues/PA-01-entity-catalog.md) |
| PA-2 | [PA-02-invocation-integrity.md](../../docs/agent-studio/issues/PA-02-invocation-integrity.md) |
| PA-3 | [PA-03-settlement-challenge.md](../../docs/agent-studio/issues/PA-03-settlement-challenge.md) |
| PA-4 | [PA-04-federation-acceptance.md](../../docs/agent-studio/issues/PA-04-federation-acceptance.md) |
| PA-5 | [PA-05-entity-acceptance-step.md](../../docs/agent-studio/issues/PA-05-entity-acceptance-step.md) |
| PA-6 | [PA-06-reputation-mcp-security.md](../../docs/agent-studio/issues/PA-06-reputation-mcp-security.md) |

## Meta Agent

<!-- e.g. Atlas-0, Mesh-0, Gauge-0 -->

## Agent Studio

Spawn mission:

```powershell
python backend/scripts/spawn_kernel_mission.py
# or POST /api/v1/agent-studio/missions/from-plan/phase_a_kernel
```

## Acceptance command

```powershell
python backend/scripts/audit_entities.py --repair
python backend/scripts/run_phase_a_acceptance.py http://127.0.0.1:8100 --federation http://127.0.0.1:8101
```

## Acceptance criteria

- [ ] 
- [ ] 
