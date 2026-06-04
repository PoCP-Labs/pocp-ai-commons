# Federation Protocol Operator Manifest v0.1

**Schema:** `pocp.federation_protocol_manifest.v0.1`  
**Wire:** `GET /api/v1/intelligence/protocol/federation`  
**Implementation:** `backend/services/protocol_federation_status/schemas.py`

Agent Studio and cross-node pilots use this surface as the **single operator entry** for stable HTTPS bindings — instance discovery, exchange spine, `/pocp/*` public node aliases, and federation import.

Related: [CROSS-NODE-INTERNET.md](./CROSS-NODE-INTERNET.md) · [BINDING-TO-DIALOGUE.md](./BINDING-TO-DIALOGUE.md) · [PUBLIC-NODE-PROTOCOL.md](./PUBLIC-NODE-PROTOCOL.md)

---

## Response fields

| Field | Description |
|-------|-------------|
| `schema` | `pocp.federation_protocol_manifest.v0.1` |
| `node_id` | `POCP_NODE_ID` |
| `base_url` | `BACKEND_URL` |
| `addrbook` | Discovered peer counts (score / ban / promotion eligibility) |
| `trusted_peer_count` | Entries from `POCP_TRUSTED_NODES` |
| `feature_flags` | `POCP_DIALOGUE_PEER_ROUTE`, auto-discover, addr relay, auto-promote |
| `promotion_policy` | Min successes, min score, trust weight, bootstrap URL |
| `endpoints` | Full operator map from `build_operator_protocol_endpoints()` |
| `exchange_import` | L1 federated exchange proof import URLs |
| `cross_node` | Connect, handshake, dialogue, overlay relay |

---

## Required `endpoints` keys (acceptance)

Validated by `validate_federation_protocol_manifest()` in `backend/services/protocol_federation_status/schemas.py`.

### Core operator surface

| Key | Purpose |
|-----|---------|
| `well_known` | Instance discovery |
| `protocol_federation` | Self-describing manifest URL |
| `wallet_quote` | Pre-flight quote (`kind: quote`) |
| `federation_exchange_import` | Cross-node exchange proof import |
| `ai_chat` | Metered LLM chat binding |
| `mcp_invoke` | Metered MCP tool binding |
| `intelligence_dialogue` | Entity dialogue + `payload.execute` |

### Phase A `/pocp/*` public node aliases

| Key | Route | Dialogue binding |
|-----|-------|------------------|
| `pocp_node` | `GET /pocp/node` | instance manifest |
| `pocp_health` | `GET /pocp/health` | liveness |
| `pocp_capabilities` | `GET /pocp/capabilities` | `discover` |
| `pocp_invoke` | `POST /pocp/invoke` | any `pocp.entity_dialogue.v0.1` kind |
| `pocp_handshake` | `POST /pocp/handshake` | federation discover + handshake |
| `pocp_proofs` | `POST /pocp/proofs` | `attest` / proof verify |
| `pocp_settlements_ack` | `POST /pocp/settlements/ack` | `finalize_notice` |
| `pocp_sync` | `GET /pocp/sync` | `federation_offer` (bulk) |

See [BINDING-TO-DIALOGUE.md](./BINDING-TO-DIALOGUE.md) for metered execute (`ai_chat`, `mcp_invoke`, `intelligence_dialogue`).

### Required `exchange_import` keys

| Key | Purpose |
|-----|---------|
| `import_exchange_proof` | L1 federated exchange proof import (no BC mint) |
| `import_proof` | Contribution proof mirror import |
| `validate_proof` | Pre-import validation |

---

## Verify locally

```bash
curl -s http://127.0.0.1:8000/api/v1/intelligence/protocol/federation | jq .
```

```bash
cd backend && python -m pytest tests/test_protocol_federation_status.py tests/test_public_node_protocol.py -q
```
