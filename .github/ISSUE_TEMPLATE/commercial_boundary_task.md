---
name: Commercial Boundary Task
about: Define commercial module boundaries
title: "[Commercial] "
labels: "commercial, open-core"
assignees: ""
---

## Goal

What commercial boundary should be defined?

## Phase & verification

| Field | Value |
|-------|-------|
| **Phase** | A · B · C (see [ROADMAP-THREE-PHASES.md](../../docs/ROADMAP-THREE-PHASES.md)) |
| **Acceptance command** | `python backend/scripts/health_check.py` |

## Module

- [ ] Advanced anti-abuse
- [ ] Commercial neural routing
- [ ] Managed compute scheduler
- [ ] Enterprise console
- [ ] Commercial API gateway
- [ ] Advanced reputation model

## Acceptance criteria

- [ ] Open-source layer is protected.
- [ ] Commercial layer is clearly separated.
- [ ] No sensitive implementation details are exposed.
