# PoCP Event Batch Spec

## Definition

EventBatch is PoCP's Bitcoin-inspired equivalent of a block.

It groups ProtocolEvents and creates a Merkle root for verification.

It does not require PoW mining.

## EventBatch Schema

```json
{
  "batch_id": "batch_001",
  "previous_batch_hash": "sha256:prev_batch",
  "event_merkle_root": "sha256:root",
  "events_count": 128,
  "created_by_node_id": "indexer_001",
  "timestamp": "2026-06-02T10:10:00Z",
  "signature": "sig_xxx"
}
```

## Why EventBatch Matters

It enables event inclusion proof, light node verification, event history compression, external anchoring, reputation replay, and settlement checkpoints.
