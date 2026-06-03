# Invocation Ledger Spec

Invocation defines what actually happened.

Current InvocationTrace can be upgraded over time with:

```text
capability_id
input_hash
output_hash
cost_unit
cost_amount
proof_id
verification_id
settlement_id
signed_event
public_node_id
nonce
```

Do not delete the existing InvocationTrace model in the first PR.
