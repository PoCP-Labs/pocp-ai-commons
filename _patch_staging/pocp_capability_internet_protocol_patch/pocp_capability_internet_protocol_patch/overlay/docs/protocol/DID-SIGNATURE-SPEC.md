# DID and Signature Spec

## Signed Event

```json
{
  "event_id": "evt_001",
  "event_type": "CapabilityPublished",
  "entity_id": "skill_001",
  "node_id": "node_001",
  "payload_hash": "sha256:...",
  "timestamp": "2026-06-02T10:00:00Z",
  "nonce": "random_nonce",
  "signature": "sig_xxx"
}
```

## Signed Request Headers

```text
X-PoCP-Node-Id
X-PoCP-Entity-Id
X-PoCP-Timestamp
X-PoCP-Nonce
X-PoCP-Body-Hash
X-PoCP-Signature
```
