# PoCP Audit Node — verify without trusting the operator

Run a **read-only mirror** that syncs proofs from a trusted peer — like a Bitcoin full node watching the chain without mining.

## Quick start (Docker)

```bash
# Terminal 1 — source node (full participant)
docker compose -f docker-compose.federation.yml up backend-a

# Terminal 2 — audit mirror (read-only)
docker compose -f docker-compose.federation.yml up backend-b
```

- Node A: http://localhost:8100
- Node B (mirror): http://localhost:8101 — `POCP_NODE_MODE=read_only_mirror`

## CLI audit (no Docker DB)

```bash
# Full remote audit: chain + anchor + wallet replay
python backend/scripts/audit_node.py remote --url http://localhost:8100

# Compare committed anchors in repo vs live node
python backend/scripts/audit_node.py anchors --dir anchors --url http://localhost:8100

# Daily issuance budget (Bitcoin-style mint caps)
curl http://localhost:8100/api/v1/issuance/budget

# Anchor includes peer_attestations when trusted peers share merkle_root + graph_merkle_root + tip_hash
curl http://localhost:8100/api/v1/ledger/anchor | jq '.cosign_summary, .graph_merkle_root, .peer_attestations'

# Graph SPV + delta sync for mirrors
curl http://localhost:8100/api/v1/graph/merkle-root
curl "http://localhost:8100/api/v1/graph/delta?since=2026-01-01T00:00:00"
```

Set `ENABLE_ANCHOR_COSIGN=false` to disable cross-node attestation collection.

## What the mirror can do

| Action | Allowed |
|--------|---------|
| GET ledger/verify, anchor, export | Yes |
| GET wallets/audit, issuance/budget | Yes |
| POST federation/import-proof | Yes |
| POST contributions (local writes) | **No** — 403 |

## Environment

| Variable | Mirror value |
|----------|--------------|
| `POCP_NODE_MODE` | `read_only_mirror` |
| `POCP_TRUSTED_NODES` | JSON list with source node |
| `POCP_FEDERATION_SYNC_ON_STARTUP` | `true` |
| `POCP_VERIFY_REMOTE_LEDGER` | `true` |

See [FEDERATION-DEMO.md](../docs/FEDERATION-DEMO.md) · [inspiration-mappings/bitcoin.md](../docs/inspiration-mappings/bitcoin.md).
