---
name: Repository Split Task
about: Plan or execute repository boundary changes
title: "[Repo] "
labels: "repository, open-core"
assignees: ""
---

## Goal

What repository boundary change should be made?

## Phase & verification

| Field | Value |
|-------|-------|
| **Phase** | A · B · C (see [ROADMAP-THREE-PHASES.md](../../docs/ROADMAP-THREE-PHASES.md)) |
| **Acceptance command** | `python backend/scripts/health_check.py` |

## Repo category

- [ ] Public
- [ ] Semi-open
- [ ] Private / commercial
- [ ] Deprecated / archived

## Acceptance criteria

- [ ] Repository purpose is clear.
- [ ] README explains status.
- [ ] Sensitive code is not placed in public repos.
- [ ] Links point to the correct active repository.
