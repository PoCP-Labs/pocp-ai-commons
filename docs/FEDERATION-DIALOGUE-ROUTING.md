# Federation peer dialogue routing (PL-4)

Mesh-0 scope: cross-node `federation_offer` / `federation_accept` over the federation dialogue surface, with trust-bundle validation on the import path.

Parent: [FEDERATION-DISCOVERY.md](./FEDERATION-DISCOVERY.md) · Protocol: [ENTITY-DIALOGUE-PROTOCOL.md](./protocol/ENTITY-DIALOGUE-PROTOCOL.md) §4.3 · Cross-node invoke: [CROSS-NODE-INTERNET.md](./protocol/CROSS-NODE-INTERNET.md)

---

## Endpoints

| Surface | Path | Auth | Use |
|---------|------|------|-----|
| Local (user session) | `POST /api/v1/intelligence/dialogue` | JWT / API key | Node A browser or script |
| Peer (federation) | `POST /api/v1/federation/dialogue` | Trust list only | Node A → Node B HTTPS forward |
| REST bindings | `POST /api/v1/federation/validate-proof` | Public | Dry-run trust bundle |
| REST bindings | `POST /api/v1/federation/import-proof` | Public | Import after validation |
| REST bindings | `POST /api/v1/federation/overlay/relay` | Public | Overlay enqueue + optional import |

`GET /api/v1/federation/node` advertises `dialogue_api: /api/v1/federation/dialogue`.

---

## Routing model

```text
Node A (importer)                         Node B (exporter)
POST /intelligence/dialogue               POST /federation/dialogue
        │                                         │
        │  federation_offer / federation_accept   │
        └──────── HTTPS (POCP_TRUSTED_NODES) ────►│
                                                  │
                                    validate_proof_against_trust_policy
                                    overlay enqueue (FederatedProofOffered)
                                    optional import_from_proof_packet
```

When `to.node_id` differs from local `POCP_NODE_ID`, kinds in `ROUTABLE_KINDS` (including `federation_offer` and `federation_accept`) may forward to the peer’s `/api/v1/federation/dialogue` when:

- `POCP_DIALOGUE_PEER_ROUTE=true` (default), and
- the target entity is not resolved locally, or
- `payload.route_peer: true` is set.

Peer resolution order: `POCP_TRUSTED_NODES` → discovered peer entity (`federation_peer` / `discovered_peer` role with routable `base_url`).

---

## `federation_offer` vs `federation_accept`

| Kind | Default `auto_import` | Trust bundle | Typical role |
|------|----------------------|--------------|--------------|
| `federation_offer` | `false` | `validate_proof_against_trust_policy` | Exporter offers proof |
| `federation_accept` | `true` | same validator; rejects when `blocking_valid` is false | Importer validates + imports |

Both kinds call the same overlay relay (`relay_federation_offer` / `federation_accept_from_proof`). Validation runs **before** overlay enqueue and import — identical rules to `POST /federation/validate-proof` and `POST /federation/import-proof`.

Shared payload fields:

| Field | Required | Meaning |
|-------|----------|---------|
| `payload.proof` | one of proof or contribution_id | Inline `pocp_contribution_proof` |
| `payload.contribution_id` | one of proof or contribution_id | Fetch from trusted peer when proof omitted |
| `payload.source_node_id` | cross-node | Trusted peer id (falls back to `from.node_id`) |
| `payload.fetch_peer` | no | Default `true` for offer |
| `payload.auto_import` | no | Run `import_from_proof_packet` after validation |

Response `result.validation` mirrors the validate-proof REST shape (`blocking_valid`, `checks[]`). `status` is `accepted` only when validation passes and import (if requested) succeeds.

---

## Example: cross-node `federation_accept`

Node A imports a proof from Node B (`peer-b`):

```json
POST https://node-a.example.com/api/v1/intelligence/dialogue
Authorization: Bearer <jwt>

{
  "schema": "pocp.entity_dialogue.v0.1",
  "dialogue_id": "dlg_fed_acc_1",
  "kind": "federation_accept",
  "from": { "entity_id": "<human-on-a>", "node_id": "node-a" },
  "to": { "entity_id": "<human-on-b>", "node_id": "peer-b" },
  "payload": {
    "source_node_id": "peer-b",
    "contribution_id": "c_approved_123",
    "auto_import": true,
    "route_peer": true
  }
}
```

Node A forwards to `https://peer-b.example.com/api/v1/federation/dialogue`. Node B fetches the proof (if needed), runs trust-bundle validation, enqueues overlay, and imports when `auto_import` is true.

Dry-run only (no import):

```json
{
  "kind": "federation_offer",
  "payload": {
    "source_node_id": "peer-b",
    "proof": { "proof_type": "pocp_contribution_proof", "...": "..." },
    "auto_import": false
  }
}
```

---

## Environment variables

| Variable | Role |
|----------|------|
| `POCP_DIALOGUE_PEER_ROUTE` | Enable cross-node dialogue forward (default `true`) |
| `POCP_TRUSTED_NODES` | JSON list `{node_id, base_url, trust_weight}` for peer routing |
| `POCP_PEER_DIALOGUE_TIMEOUT` | HTTP timeout seconds for peer forward (default 120) |
| `POCP_PEER_DIALOGUE_HMAC` | Optional shared secret — HMAC-SHA256 over canonical dialogue body on `POST /federation/dialogue` (CIP-P3.3) |
| `POCP_PEER_DIALOGUE_HMAC_REQUIRED` | When `true` and secret set, reject unsigned or invalid dialogue POSTs (default `false`) |
| `POCP_PEER_DIALOGUE_HMAC_TRUSTED_ONLY` | When `true`, require signing `node_id` in `POCP_TRUSTED_NODES` |
| `POCP_PEER_DIALOGUE_HMAC_SKEW_SECONDS` | Clock skew for dialogue HMAC timestamps (default 120) |
| `POCP_NODE_ID` | Local node id in `from` / `to` refs |
| `BACKEND_URL` | Advertised base URL in federation manifest |

See also [FEDERATION-DISCOVERY.md](./FEDERATION-DISCOVERY.md) for discovery, handshake, and bootstrap env vars.

### Optional peer dialogue HMAC (CIP-P3.3)

When both peers set the same `POCP_PEER_DIALOGUE_HMAC`, outbound forwards from `dialogue_route` attach:

| Header | Purpose |
|--------|---------|
| `X-POCP-Dialogue-Node-Id` | Signing node (`from.node_id` on originator) |
| `X-POCP-Dialogue-Nonce` | Replay guard |
| `X-POCP-Dialogue-Timestamp` | Unix seconds |
| `X-POCP-Dialogue-Body-Digest` | SHA-256 of sorted JSON body |
| `X-POCP-Dialogue-Signature-Alg` | `hmac-sha256` |
| `X-POCP-Dialogue-Signature` | HMAC over `pocp-dialogue-v1\|{node_id}\|{nonce}\|{ts}\|{digest}` |

Receiver verifies on `POST /api/v1/federation/dialogue` before `route_dialogue`. With secret unset, behavior is unchanged (no headers). Set `POCP_PEER_DIALOGUE_HMAC_REQUIRED=true` on hardened peers to reject unsigned traffic. Threat model: [THREAT-MODEL-v0.1.md](./protocol/THREAT-MODEL-v0.1.md).

---

## Cross-node quote → invoke → receipt (CIP-P2.1)

Node A (consumer) routes `quote` and `invoke` to Node B via peer dialogue. Execution receipts are returned from the peer; **exchange_settled** is recorded on the **originator** (Node A) with `payload.peer_route: true` and `refs.originator_exchange_id` on the dialogue response.

| Step | `kind` | Origin | Settlement |
|------|--------|--------|------------|
| 1 | `quote` | A → B | `exchange_settled` audit on A (`peer_route.quote.v1`) |
| 2 | `invoke` | A → B | trace stub on A + `exchange_settled` on A (`peer_route.invoke_trace.v1` or metered `peer_route.invoke.v1`) |
| 3 | receipt | peer response | `refs.invocation_trace_id` / capability receipt metadata from B |

Docker A/B acceptance:

```bash
docker compose -f docker-compose.federation.yml up -d --build
python scripts/cross_node_exchange_acceptance.py http://127.0.0.1:8100 http://127.0.0.1:8101
```

Included in `run_phase_a_acceptance.py --federation` as step `cross_node_exchange_acceptance`.

---

## Verification

```bash
cd backend
python -m pytest tests/test_dialogue_peer_route.py -q
python -m pytest tests/ -k "test_federation or test_entity_dialogue or test_trust_policy_bundle" -q
python scripts/run_phase_a_acceptance.py http://127.0.0.1:8100 --federation http://127.0.0.1:8101
```
