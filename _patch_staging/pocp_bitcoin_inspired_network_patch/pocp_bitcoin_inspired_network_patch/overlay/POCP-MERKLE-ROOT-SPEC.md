# PoCP Merkle Root Spec

## Purpose

Merkle roots let light nodes verify that a ProtocolEvent was included in an EventBatch without downloading every event.

## Event Hash

```text
event_hash = sha256(canonical_json(protocol_event))
```

## Uses

```text
Proof inclusion
Settlement inclusion
Reputation update inclusion
EventBatch anchoring
light node verification
```
