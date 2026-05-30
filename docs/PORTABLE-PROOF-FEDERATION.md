# Portable Proof and Federation Surface

PoCP has three related public surfaces that should be read together:

1. `GET /api/v1/graph` shows the local contribution relationship graph.
2. `GET /api/v1/contributions/{contribution_id}/proof` exports one contribution as a portable proof packet.
3. `POST /api/v1/federation/import-proof` imports an approved proof packet from a trusted peer node.

The graph is the live local view. The proof packet is the portable object. Federation is the trust boundary where another node decides whether that portable object can affect local reputation.

## Relationship

```text
local ledger + participants + invocations
        |
        v
GET /api/v1/graph
        |
        | contribution-scoped edges are copied into
        v
GET /api/v1/contributions/{id}/proof
        |
        | integrity.proof_hash may be signed by the source node
        v
POST /api/v1/federation/import-proof
        |
        | trusted import applies reputation only, not local AI Credits
        v
federated reputation by portable_id
```

## Graph Surface

`services/graph.py` builds the node-local graph from:

- entities, owner links, and creator links;
- approved, AI-verified, and submitted contribution participants;
- invocation traces, including LLM provider nodes.

Each contribution-related edge carries `contribution_id`. That identifier is the bridge from the broad graph view to a specific portable proof packet.

## Proof Packet Surface

`services/proof.py` builds a `pocp_contribution_proof` packet for one contribution. The packet includes:

- contribution event metadata;
- entity identity snapshots and participant roles;
- evidence content hash and raw evidence;
- AI advisory verification and human review records;
- `contribution_graph.edges` for the contribution-local graph;
- rights, reputation, and ledger audit material;
- `integrity.proof_hash`.

When `POCP_NODE_PRIVATE_KEY` is configured, the packet also includes a `federation` block. The source node signs `integrity.proof_hash`, so a peer node can verify that the exported proof was not changed after signing.

## Federation Surface

`backend/routers/federation.py` exposes the public federation contract:

- `GET /api/v1/federation/node` advertises node metadata, public key, and export/import endpoints.
- `GET /api/v1/federation/trust` returns configured trusted peer nodes.
- `POST /api/v1/federation/import-proof` accepts a portable contribution proof packet.
- `GET /api/v1/federation/reputation?portable_id=...` returns reputation aggregated around a portable identity.

`services/federation_import.py` currently imports only approved proof packets. It resolves participants by `portable_id`, verifies the optional or required signature, applies trust-weighted reputation, and records a `federation_import` ledger event. It does not mint local AI Credits for imported work.

## Stable Interop Rules

- Local UUIDs are node-local. Cross-node identity should use `metadata.portable_id`.
- A graph edge that needs to travel should be inside a contribution proof packet, not inferred only from `GET /api/v1/graph`.
- Peer nodes should verify `integrity.proof_hash` before importing signed proofs.
- Imported proofs affect reputation according to local trust policy; local rights issuance remains local.

## Minimal Flow

```bash
# Source node: inspect the contribution-local proof and optional signature.
curl http://localhost:8100/api/v1/contributions/{contribution_id}/proof

# Target node: import the approved proof packet from a trusted source node.
curl -X POST http://localhost:8101/api/v1/federation/import-proof \
  -H "Content-Type: application/json" \
  -d '{"source_node_id":"community-a","proof":{...}}'

# Target node: read the imported reputation by portable identity.
curl "http://localhost:8101/api/v1/federation/reputation?portable_id=github:rain"
```

See also [CONTRIBUTION-PROOF-PACKET-v0.1.md](./CONTRIBUTION-PROOF-PACKET-v0.1.md), [FEDERATION-v0.1.md](./FEDERATION-v0.1.md), [FEDERATION-DEMO.md](./FEDERATION-DEMO.md), and [CORE-TECH-STACK.md](./CORE-TECH-STACK.md).
