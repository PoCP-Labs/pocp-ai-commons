# Agent Governance Toolkit → PoCP Peer Trust

**Source:** [microsoft/agent-governance-toolkit](https://github.com/microsoft/agent-governance-toolkit) · Benchmark: [DISTRIBUTED-INTELLIGENCE-BENCHMARK.md](../DISTRIBUTED-INTELLIGENCE-BENCHMARK.md)

## What to borrow

| AGT / AgentMesh concept | PoCP mapping |
|-------------------------|--------------|
| Human sponsor on agent identity | Entity `owner_id` + accountability block |
| Ed25519 agent keys | Federation keys + `X-POCP-Peer-Signature-Alg: ed25519` |
| Short-lived credentials | Timestamp + nonce TTL (`POCP_PEER_HANDSHAKE_TTL_SECONDS`) |
| Trust handshake (challenge-response) | `GET /compute/peer/challenge` + HMAC/Ed25519 verify |
| Merkle audit log | Optional export block on Proof packet (future) |

## What to reject

- Auto-gating finalization from trust score alone
- Ring tiers replacing human review
- Enterprise compliance mapping as hard dependency

## Endpoints (shipped BI-2)

| Endpoint | Purpose |
|----------|---------|
| `GET /api/v1/intelligence/compute/peer/trust` | Handshake manifest |
| `GET /api/v1/intelligence/compute/peer/challenge` | Issue one-time nonce (challenge mode) |

## Required headers (handshake)

```http
X-POCP-Peer-Node-Id: node-a
X-POCP-Peer-Nonce: {uuid}
X-POCP-Peer-Timestamp: {unix_seconds}
X-POCP-Peer-Signature: {hex}
X-POCP-Peer-Signature-Alg: hmac-sha256   # or ed25519
```

Legacy `X-POCP-Peer-Secret` still accepted when shared secret matches.

## Modes

| `POCP_PEER_HANDSHAKE_MODE` | Behavior |
|----------------------------|----------|
| `shared_secret` (default) | Client nonce + HMAC; replay blocked in-process |
| `challenge` | Nonce must come from `/compute/peer/challenge` |

Outbound peer calls (`witness`, `inference`, MCP) auto-attach headers via `build_peer_auth_headers()`.

## Code

- `backend/services/peer_trust.py`
- `backend/services/peer_compute.py` — `validate_peer_witness_request`
- `backend/services/verifiers/peer_witness_verifier.py`
- `backend/services/compute_executor.py`
- `backend/services/peer_mcp.py`

## Status

**active (BI-2 partial)** — registry entry `agent_governance_toolkit` in `neural_network_sources.yaml`.

Not yet: Merkle audit log export on Proof packet, trust score tiers.
