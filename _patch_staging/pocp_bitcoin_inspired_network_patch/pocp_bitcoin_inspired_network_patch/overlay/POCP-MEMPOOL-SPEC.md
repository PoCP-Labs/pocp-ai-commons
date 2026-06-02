# PoCP Mempool Spec

## Definition

PoCP Mempool is a set of pending protocol events waiting for validation, verification, settlement, or batching.

## Pools

```text
PendingInvocationPool
PendingProofPool
PendingVerificationPool
PendingSettlementPool
PendingChallengePool
```

## Validation

A mempool event should be checked for:

```text
valid signature
valid timestamp
valid nonce
known Entity
known Node
valid Capability
valid event type
non-duplicate payload hash
risk level
rate limits
```
