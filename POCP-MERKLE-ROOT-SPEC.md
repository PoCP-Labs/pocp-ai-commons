# PoCP Merkle Root Spec

## Purpose

Merkle roots let light nodes verify that a ProtocolEvent was included in an EventBatch without downloading every event.

## Event Hash

```text
event_hash = sha256(canonical_json(protocol_event))
```

Display form: `sha256:<hex>` (leaf). Merkle tree uses **bare hex** leaves with the same
`sha256-pair-concat-v0.1` algorithm as `ledger_merkle` — see `backend/services/merkle_canonical.py`.

## Uses

```text
Proof inclusion
Settlement inclusion
Reputation update inclusion
EventBatch anchoring
light node verification
```
