# PoCP Ledger Anchors

Public Merkle-root snapshots of PoCP node ledgers. Anyone can verify integrity without trusting a single operator.

## Layout

```text
anchors/
  {node_id}/
    ledger-anchor-YYYYMMDD.json
```

## Anchor file

```json
{
  "spec_version": "0.1",
  "anchor_type": "pocp_ledger_merkle_root",
  "node_id": "node-a",
  "merkle_root": "...",
  "ledger_valid": true,
  "tip_hash": "...",
  "federation": {
    "public_key": "...",
    "signature": "...",
    "signed_field": "merkle_root"
  }
}
```

## How anchors are produced

| Method | Command |
|--------|---------|
| Local (with DB) | `cd backend && python scripts/anchor_ledger.py ../anchors` |
| Remote API | `python scripts/fetch_anchor.py https://node.example ../anchors` |
| API endpoint | `GET /api/v1/ledger/anchor` |
| GitHub Action | `.github/workflows/ledger-anchor.yml` (daily + manual) |

## Verify

```bash
# Full remote node audit (chain + anchor + wallets)
python backend/scripts/audit_node.py remote --url https://node.example

# Compare committed anchors vs live node
python backend/scripts/audit_node.py anchors --dir anchors --url https://node.example

# Verify SPV Merkle inclusion bundle
python backend/scripts/audit_node.py merkle --file merkle_proof.json
```

Manual steps:

1. Fetch live anchor: `GET /api/v1/ledger/anchor`
2. Compare `merkle_root` with committed file for same date
3. Optionally verify `federation.signature` against node `public_key` from `GET /api/v1/federation/node`
4. Recompute wallet balances: `GET /api/v1/wallets/audit`

---

*Anchors are append-only public memory — not owned by any single deployer.*
