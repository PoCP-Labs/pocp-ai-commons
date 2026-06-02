---
name: Formatting Task
about: Fix code formatting without changing business logic
title: "[Formatting] "
labels: "formatting, repository-health"
assignees: ""
---

## Goal

Format source files for readability.

## Phase & verification

| Field | Value |
|-------|-------|
| **Phase** | A · B · C (see [ROADMAP-THREE-PHASES.md](../../docs/ROADMAP-THREE-PHASES.md)) |
| **Acceptance command** | `python backend/scripts/health_check.py` |

## Files

- 

## Rules

- Do not change business logic.
- Do not redesign architecture.
- Run formatter if available.
- Run health check after changes.

## Acceptance criteria

- [ ] Files are readable.
- [ ] Long one-line Python files are fixed.
- [ ] Health check runs.
