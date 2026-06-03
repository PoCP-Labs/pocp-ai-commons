---
name: Capability Internet Protocol Task
about: Build PoCP as the AI capability and compute internet protocol
title: "[CIP] "
labels: "capability-internet, protocol, neural-commons"
assignees: ""
---

## Goal

What part of the Capability Internet Protocol should be added or improved?

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
- [ ] Identity / DID
- [ ] Public Node
- [ ] Capability
- [ ] Discovery
- [ ] Invocation
- [ ] Proof
- [ ] Verification
- [ ] Settlement
- [ ] TokenAccount
- [ ] ReputationGraph
- [ ] EventLog
- [ ] P2P

## Acceptance Criteria

- [ ] Schema or model exists.
- [ ] Service or API exists.
- [ ] Protocol event is considered.
- [ ] Existing AI Commons demo is not broken.
- [ ] No public token issuance is introduced.
- [ ] No secrets or private keys are committed.
