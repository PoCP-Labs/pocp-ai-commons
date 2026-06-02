---
name: Security Policy Task
about: Improve security reporting or security boundaries
title: "[Security] "
labels: "security"
assignees: ""
---

## Goal

What security process or boundary should be improved?

## Phase & verification

| Field | Value |
|-------|-------|
| **Phase** | A · B · C (see [ROADMAP-THREE-PHASES.md](../../docs/ROADMAP-THREE-PHASES.md)) |
| **Acceptance command** | `python backend/scripts/run_phase_a_acceptance.py http://127.0.0.1:8000` |

## Area

- [ ] Vulnerability reporting
- [ ] Wallet / credits security
- [ ] Ledger integrity
- [ ] Anti-abuse
- [ ] Replay attack
- [ ] Secrets management
- [ ] API security

## Acceptance criteria

- [ ] Security guidance is clear.
- [ ] Sensitive exploit details are not exposed.
- [ ] Reporting path is documented.
