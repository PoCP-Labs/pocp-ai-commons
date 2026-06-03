# Capability Internet Mission — Agent Studio MANIFEST

**Plan id:** `capability_internet`  
**Nexus track:** `capability_internet`  
**Issues:** CI-1 .. CI-12 (see [CAPABILITY-INTERNET-BACKLOG.md](../../docs/agent-studio/CAPABILITY-INTERNET-BACKLOG.md))

## Wave status

| Wave | Scope | Status |
|------|-------|--------|
| **Wave 1** | CI gate: `audit_entities --repair`, federation acceptance, minimum living checklist | **Closed** 2026-06-03 — [WAVE-1-GATE.md](./WAVE-1-GATE.md) · handoff `bc91cffd` |
| Wave 2+ | CI-1..CI-12 domain handoffs, CIP in CI, production API wire | Open |

## North star

Implement the **12-layer capability internet** in `pocp-ai-commons` without building a centralized platform. Minimum living network first.

## Prerequisites

- Phase A kernel handoffs progressing (PA-1..PA-4)
- Cursor automation on host: `py -3.12` + `cursor-sdk` + `.\scripts\run-studio-super-loop.ps1`

## Layer owners (Meta Agents)

| Layer | Primary | Support |
|-------|---------|---------|
| Entity, Node, Identity | Atlas-0 | Vault-0 |
| Capability, Discovery, Invocation | Pulse-0 | Mesh-0 |
| Proof, Settlement | Vault-0 | Prism-0 |
| Verification | Forge-0 | Sentinel-0 |
| Reputation, Governance | Sentinel-0 | Lex-0 |
| Economy | Prism-0 | Lex-0 |
| Docs | Herald-0 | Compass-0 |
| Acceptance | Gauge-0 | — |

## Do not

- Launch public token
- Replace rule-based routing with commercial optimizer
- Require single central server for join
- Skip invocation ledger when adding settlement

## Spawn

```powershell
python backend/scripts/spawn_capability_internet_mission.py
```
