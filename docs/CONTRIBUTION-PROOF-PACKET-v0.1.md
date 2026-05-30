# Contribution Proof Packet v0.1

The Contribution Proof Packet is PoCP's portable proof object.

It is the protocol-level artifact that allows a contribution to be inspected, exported, verified, signed, mirrored, and optionally imported by another PoCP node.

## Identity

| Field | Value |
|---|---|
| `proof_type` | `pocp_contribution_proof` |
| `proof_schema` | `pocp.contribution_proof.v0.1` |
| `spec_version` | `0.1` |
| Endpoint | `GET /api/v1/contributions/{contribution_id}/proof` |

## Covered PoCP Native Layers

Every proof packet declares the protocol layers it covers:

```json
[
  "entity_identity",
  "contribution_event",
  "contribution_participant",
  "evidence_hash",
  "human_ai_verification_state",
  "contribution_graph",
  "contribution_to_rights_conversion",
  "ledger_memory"
]
```

## Required Sections

| Section | Purpose |
|---|---|
| `contribution_event` | The task, contributor, contribution type, description, status, and creation time |
| `entity_identity` | Primary entity plus participant identity snapshots, roles, weights, and participant evidence |
| `evidence` | Raw evidence, normalized evidence items, content hash, and evidence spec version |
| `verification` | AI advisory verification, human review, and the rule: AI advises; humans approve; ledger remembers |
| `contribution_graph` | Contribution-scoped graph nodes, edges, and invocation traces |
| `rights_and_reputation` | CP / BC transactions and reputation state associated with the contribution |
| `ledger_audit` | Ledger records and record hashes linked to the contribution |
| `integrity` | Evidence hash, ledger tip hash, proof hash, hash algorithm, and canonicalization rule |
| `federation` | Optional source node signature metadata |

## Hashing Rule

The `integrity.proof_hash` is a SHA-256 hash of the canonical proof packet.

Canonicalization:

```text
json-sort-keys-compact-excludes-generated_at-federation-proof_hash
```

This means:

- sort JSON keys;
- use compact separators;
- encode as UTF-8;
- exclude `generated_at`;
- exclude `federation`;
- exclude `integrity.proof_hash` itself.

The generated timestamp can change between exports without changing the proof hash. A federation signature can be added without changing the proof hash.

## Federation Signature

If `POCP_NODE_PRIVATE_KEY` is configured, the source node signs `integrity.proof_hash` and adds:

```json
{
  "federation": {
    "node_id": "source-node",
    "public_key": "ed25519-public-key-hex",
    "signature": "ed25519-signature-hex",
    "signed_field": "integrity.proof_hash"
  }
}
```

Importing nodes must verify:

1. `proof_type == "pocp_contribution_proof"`;
2. contribution status is `approved`;
3. `integrity.proof_hash` matches the packet content;
4. federation signature is valid when required by local policy;
5. source node is trusted unless local policy allows untrusted import.

## Boundary

Proof import may apply trust-weighted reputation.

Proof import must not mint local BC / AI Credits by default. Local usage rights remain local unless a governance process explicitly accepts external rights issuance.

## Minimal Shape

```json
{
  "spec_version": "0.1",
  "proof_type": "pocp_contribution_proof",
  "proof_schema": "pocp.contribution_proof.v0.1",
  "proof_id": "pocp-proof:<contribution-id>",
  "generated_at": "2026-05-29T00:00:00Z",
  "protocol_layers": ["entity_identity", "contribution_event"],
  "contribution_event": {},
  "entity_identity": {},
  "evidence": {},
  "verification": {},
  "contribution_graph": {},
  "rights_and_reputation": {},
  "ledger_audit": {},
  "integrity": {
    "hash_algorithm": "sha256",
    "canonicalization": "json-sort-keys-compact-excludes-generated_at-federation-proof_hash",
    "evidence_hash": "...",
    "ledger_tip_hash": "...",
    "proof_hash": "..."
  }
}
```
