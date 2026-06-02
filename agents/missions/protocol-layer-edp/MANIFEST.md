# Protocol Layer — Entity Dialogue Protocol

**Mission plan id:** `protocol_layer_edp`  
**North star:** Native L2 dialogue envelope — not a REST/A2A/MCP 拼装车.

Source docs:

- [docs/protocol/ENTITY-DIALOGUE-PROTOCOL.md](../../docs/protocol/ENTITY-DIALOGUE-PROTOCOL.md)
- [docs/protocol/ENTITY-CONNECTION.md](../../docs/protocol/ENTITY-CONNECTION.md)
- [docs/protocol/TRUST-POLICY-BUNDLE.md](../../docs/protocol/TRUST-POLICY-BUNDLE.md)
- [docs/protocol/CHAIN-AND-NODE-PLAN-v0.1.md](../../docs/protocol/CHAIN-AND-NODE-PLAN-v0.1.md)

## Issue → PA (Plan Action / Handoff) map

| Issue | Title | PA assignee | Exit signal |
|-------|-------|-------------|-------------|
| **PL-1** | EDP v0.1 spec + ontology cross-links | Atlas-0 | protocol doc review PASS |
| **PL-2** | Dialogue invoke → metered `capability_execute` | Pulse-0 | pytest invoke + execute |
| **PL-3** | `quote` kind + Exchange Spine binding | Vault-0 | pytest exchange_spine + dialogue |
| **PL-4** | `federation_accept` + peer dialogue routing | Mesh-0 | federation + dialogue tests |
| **PL-5** | REST/A2A → dialogue binding map | Atlas-0 + Pulse-0 | BINDING-TO-DIALOGUE.md |
| **PL-6** | Proof packet carries `dialogue_id` refs | Vault-0 | proof export test |
| **PL-7** | Entity Dialogue UI panel | Canvas-0 | npm run build |
| **PL-8** | LOCAL-SETUP + README dialogue examples | Herald-0 | docs review |
| **PL-9** | Protocol layer acceptance gate | Gauge-0 | pytest protocol + entity_dialogue |
| **PL-10** | Nexus consolidate + mission complete | Nexus-0 | all PAs completed |

## Dispatch

**UI:** Agent Studio → start plan **`protocol_layer_edp`**

**API:**

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/agent-studio/missions/from-plan/protocol_layer_edp"
```

**Script (mission + optional GitHub Issues + Cursor):**

```bash
python backend/scripts/dispatch_protocol_layer_studio.py --create-issues --cursor-tick
```

## Automation chain

```text
Nexus-0  →  spawn handoffs (PAs)
         →  Cursor worker picks pending PA
         →  Meta Agent implements within writable_paths
         →  Gauge-0 records outcome
         →  Nexus learning cycle
```

See [agents/WORKFLOW.md](../WORKFLOW.md) · [agents/CURSOR-AUTOMATION.md](../CURSOR-AUTOMATION.md)
