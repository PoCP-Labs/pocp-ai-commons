# Proof Spec

Proof defines how an Entity proves what it did.

Minimal fields:

```text
proof_id
entity_id
node_id
proof_type
task_id
invocation_id
input_hash
output_hash
evidence_ref
signature
```

Rule:

```text
Proof requires invocation_id unless proof_type is human_evidence.
```
