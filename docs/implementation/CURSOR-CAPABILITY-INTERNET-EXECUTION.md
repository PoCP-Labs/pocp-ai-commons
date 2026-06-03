# Cursor — Capability Internet Execution

Checklist for landing the Capability Internet Protocol in `pocp-ai-commons` without breaking the Genesis loop.

North star: [CAPABILITY-INTERNET-PROTOCOL.md](../CAPABILITY-INTERNET-PROTOCOL.md) · Layer map: [POCP-NETWORK-ARCHITECTURE.md](../POCP-NETWORK-ARCHITECTURE.md)

## Execution order

1. **Docs first** — positioning, layer specs, protocol index, onboarding (Herald-0)
2. **CIP skeleton** — `backend/services/cip/` in-memory modules (Forge-0 / Pulse-0)
3. **Minimum living demo** — `python backend/scripts/minimum_living_network.py` (Gauge-0)
4. **Issue template** — `.github/ISSUE_TEMPLATE/cip_runtime_task.md` with Phase & verification
5. **Import checks** — `python backend/scripts/health_check.py`
6. **Do not force P2P** — libp2p/DHT is Phase B; federation acceptance stays the Phase A gate

## Staged PR sequence

See [STAGED-PR-PLAN.md](./STAGED-PR-PLAN.md):

| PR | Scope |
|----|-------|
| 1 | Repo health + README reposition |
| 2 | Protocol docs (CIP layer specs) |
| 3 | CIP skeleton + in-memory demo |
| 4 | Runtime APIs (nodes, capabilities, invocations, …) |
| 5 | Public Node MVP |

## Agent Studio

Spawn mission:

```powershell
python backend/scripts/spawn_capability_internet_mission.py
# or POST /api/v1/agent-studio/missions/from-plan/capability_internet
```

Backlog: [CAPABILITY-INTERNET-BACKLOG.md](../agent-studio/CAPABILITY-INTERNET-BACKLOG.md)

## Verification commands

| Gate | Command |
|------|---------|
| CIP demo | `python backend/scripts/minimum_living_network.py` |
| Phase A loop | `python backend/scripts/run_phase_a_acceptance.py http://127.0.0.1:8100 --federation http://127.0.0.1:8101` |
| Entity dialogue | `cd backend && python -m pytest -q tests/test_entity_dialogue.py` |
| Meta agents | `python backend/scripts/ensure_meta_agents.py` |
| Health | `python backend/scripts/health_check.py` |

## Do not

- Replace production `services/invocation.py` / wallets in the first PR
- Launch public token issuance
- Skip invocation ledger when adding settlement
- Block local optimization P0 (Exchange Spine + Wallet) on CIP work
