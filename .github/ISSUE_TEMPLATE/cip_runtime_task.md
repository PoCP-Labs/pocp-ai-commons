---
name: CIP Runtime Task
about: Add runtime support for PoCP Capability Internet Protocol
title: "[CIP] "
labels: "cip, protocol, neural-commons"
assignees: ""
---

## Goal

What part of the CIP chain should be added or improved?

## Phase & verification

| Field | Value |
|-------|-------|
| **Phase** | A · B · C (see [ROADMAP-THREE-PHASES.md](../../docs/ROADMAP-THREE-PHASES.md)) |
| **CIP demo** | `python backend/scripts/minimum_living_network.py` |
| **Phase A loop** | `python backend/scripts/run_phase_a_acceptance.py http://127.0.0.1:8100 --federation http://127.0.0.1:8101` |

Spec index: [docs/protocol/README.md](../../docs/protocol/README.md) · Mission: [agents/missions/capability-internet/MANIFEST.md](../../agents/missions/capability-internet/MANIFEST.md)

## Layer

- [ ] Entity
- [ ] Node
- [ ] Capability
- [ ] Discovery
- [ ] Invocation
- [ ] Proof
- [ ] Verification
- [ ] Settlement
- [ ] TokenAccount
- [ ] Reputation
- [ ] EventLog
- [ ] Public Node

## Acceptance criteria

- [ ] Does not break existing AI Commons Genesis Loop.
- [ ] Does not introduce public token issuance.
- [ ] Does not require unsafe secrets.
- [ ] Has smoke/demo test coverage where possible.
