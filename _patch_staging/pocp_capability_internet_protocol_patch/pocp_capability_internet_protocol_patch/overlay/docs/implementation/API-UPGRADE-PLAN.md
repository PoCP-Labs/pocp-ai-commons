# API Upgrade Plan

## New Core APIs

```http
POST /api/v1/entities
POST /api/v1/nodes/register
POST /api/v1/nodes/{node_id}/heartbeat
GET  /api/v1/nodes/discover
POST /api/v1/capabilities
GET  /api/v1/capabilities
POST /api/v1/invocations
GET  /api/v1/invocations/{invocation_id}
POST /api/v1/proofs
POST /api/v1/proofs/{proof_id}/verify
POST /api/v1/settlements
GET  /api/v1/token-accounts/{entity_id}
GET  /api/v1/reputation/{entity_id}
GET  /api/v1/graph/entities/{entity_id}
GET  /api/v1/protocol-events
```
