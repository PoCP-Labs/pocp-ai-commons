# Protocol Native Stack — Dialogue L2 + Event Overlay L1.5

**Mission plan id:** `protocol_native_stack`  
**North star:** One native envelope and overlay — not REST/MCP adapters as the semantic core.

Source docs:

- [docs/protocol/PROTOCOL-EVENT-NETWORK.md](../../../docs/protocol/PROTOCOL-EVENT-NETWORK.md)
- [docs/protocol/BINDING-TO-DIALOGUE.md](../../../docs/protocol/BINDING-TO-DIALOGUE.md)
- [docs/protocol/ENTITY-DIALOGUE-PROTOCOL.md](../../../docs/protocol/ENTITY-DIALOGUE-PROTOCOL.md)

## Handoff map (PN-1..PN-6)

| ID | Scope | Assignee | Exit signal |
|----|-------|----------|-------------|
| **PN-1** | Five-layer stack + BINDING-TO-DIALOGUE | Atlas-0 | doc review |
| **PN-2** | Dialogue invoke + overlay emit | Pulse-0 | pytest dialogue + network |
| **PN-3** | EventBatch Merkle ↔ ledger | Vault-0 | pytest merkle |
| **PN-4** | Federation overlay relay | Mesh-0 | pytest federation overlay |
| **PN-5** | Protocol stack UI | Canvas-0 | npm run build |
| **PN-6** | Acceptance gate | Gauge-0 | smoke + pytest green |

## Dispatch

```bash
py -3.12 backend/scripts/dispatch_protocol_native_stack_studio.py --gate --cursor-tick
python backend/scripts/protocol_layer_acceptance.py
python backend/scripts/complete_protocol_missions.py
py -3.12 backend/scripts/run_studio_cursor_worker.py --once --verbose
```

**API:** `POST /api/v1/agent-studio/missions/from-plan/protocol_native_stack`

**Overlay status:** `GET /api/v1/federation/overlay/status`
