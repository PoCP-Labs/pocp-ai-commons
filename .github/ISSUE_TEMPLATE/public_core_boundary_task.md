---
name: Public Core Boundary Task
about: Clarify what belongs in public core vs commercial reserved layer
title: "[Open Core] "
labels: "open-core, architecture"
assignees: ""
---

## Goal

What boundary should be clarified?

## Phase & verification

| Field | Value |
|-------|-------|
| **Phase** | A · B · C (see [ROADMAP-THREE-PHASES.md](../../docs/ROADMAP-THREE-PHASES.md)) |
| **Acceptance command** | `python backend/scripts/health_check.py` |

## Area

- [ ] Protocol schema
- [ ] Reference implementation
- [ ] Anti-abuse
- [ ] Routing
- [ ] Reputation
- [ ] Settlement
- [ ] Compute
- [ ] Enterprise
- [ ] API gateway

## Acceptance criteria

- [ ] Public-core rule is clear.
- [ ] Commercial-reserved rule is clear.
- [ ] Sensitive logic is not exposed.
