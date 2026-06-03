# Minimum Living Network Demo

In-memory reference for the **12-layer Capability Internet** (`backend/services/cip/`). This demo does **not** replace the Genesis MVP loop or federation acceptance.

Parent: [MINIMUM-LIVING-NETWORK.md](../MINIMUM-LIVING-NETWORK.md) · Spec index: [protocol/README.md](../protocol/README.md)

## Run

```bash
python backend/scripts/minimum_living_network.py
```

Expected output ends with:

```text
[OK] minimum_living_network passed.
Invocation: <invocation_id>
Settlement: <settlement_id>
Events: <count>
```

## What the demo exercises

| Step | CIP module | Output key |
|------|------------|------------|
| Register skill node | `services/cip/node/` | `skill_node` |
| Publish `code_review` capability | `services/cip/capability/` | `capability` |
| Discover + invoke | `services/cip/discovery/`, `services/cip/invocation/` | `invocation` |
| Submit proof | `services/cip/proof/` | `proof` |
| AI verification | `services/cip/verification/` | `verification` |
| Multi-party settlement | `services/cip/settlement/` | `settlement` |
| Token accounts | `services/cip/economy/` | `accounts` |
| Reputation edge | `services/cip/reputation/` | `skill_reputation` |
| Append-only events | `services/cip/events/` | `events` |

## Exit criteria mapping

See [MINIMUM-LIVING-NETWORK.md](../MINIMUM-LIVING-NETWORK.md) § Exit criteria. The in-memory demo satisfies the **logical chain** (invoke → proof → verify → settle → reputation → events). Federation import and production wallet replay remain Phase A acceptance gates.

## Related

- Agent Studio mission: [capability_internet](../../agents/missions/capability-internet/MANIFEST.md)
- Staged PR plan: [STAGED-PR-PLAN.md](./STAGED-PR-PLAN.md)
- Issue template: [.github/ISSUE_TEMPLATE/cip_runtime_task.md](../../.github/ISSUE_TEMPLATE/cip_runtime_task.md)
