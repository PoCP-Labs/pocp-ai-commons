# ProtocolEvent Spec

ProtocolEvent is an append-only signed record of meaningful protocol activity.

```json
{
  "event_id": "evt_001",
  "event_type": "InvocationCreated",
  "entity_id": "agent_001",
  "node_id": "node_001",
  "payload_hash": "sha256:payload",
  "timestamp": "2026-06-02T10:00:00Z",
  "nonce": "random_nonce",
  "signature": "sig_xxx",
  "previous_event_hash": "sha256:previous"
}
```
