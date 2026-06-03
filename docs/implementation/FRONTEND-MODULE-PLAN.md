# Frontend Module Plan

Recommended frontend areas:

- Entity Registry
- Capability Registry
- Task Center
- Neural Routing Plan View
- Invocation Ledger
- Wallet / Token Account
- Settlement Explorer
- Reputation View
- Neural Graph Explorer

First target:

Show how a task moves through route, invoke, verify, settle, reputation, and graph.

## Entity Dialogue (PL-7)

**Component:** `frontend/src/ProtocolDialoguePanel.jsx`  
**Surface:** Entities tab → `EntityDetail` → **Entity Dialogue** section

| Action | Dialogue `kind` | API |
|--------|-----------------|-----|
| Ping | `ping` | `POST /api/v1/intelligence/entities/{entity_id}/dialogue` |
| Discover | `discover` | same |
| Invoke | `invoke` (+ optional metered `execute`) | same |

Envelope schema: `pocp.entity_dialogue.v0.1` (see `docs/protocol/ENTITY-DIALOGUE-PROTOCOL.md`). Requires Dev Login so `from.entity_id` is set from the session.
