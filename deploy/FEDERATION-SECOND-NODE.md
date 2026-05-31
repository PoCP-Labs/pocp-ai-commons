# PoCP Federation — second independent operator (Epic D1)

**Goal:** Run a production node that is **not** Genesis — separate VPS, Postgres, keys, domain — and optionally trust or mirror Genesis / peer nodes.

See: [docs/FEDERATION-OPERATOR-RUNBOOK.md](../docs/FEDERATION-OPERATOR-RUNBOOK.md) · [docs/FEDERATION-DEMO.md](../docs/FEDERATION-DEMO.md)

---

## 1. Generate node identity

On the **new** server (never reuse Genesis private keys):

```bash
python backend/scripts/generate_node_keys.py school-node-1
```

Save output to a secrets manager. Example:

```bash
POCP_NODE_ID=school-node-1
POCP_NODE_PRIVATE_KEY=<hex>
POCP_NODE_PUBLIC_KEY=<hex>
```

---

## 2. Configure environment

Copy and edit:

```bash
cp deploy/federation-node.env.example backend/.env
```

| Variable | Operator node | Mirror node |
|----------|---------------|-------------|
| `POCP_NODE_ID` | unique id | unique id |
| `POCP_NODE_PRIVATE_KEY` | new key | new key |
| `POCP_NODE_MODE` | `full` (default) | `read_only_mirror` |
| `POCP_TRUSTED_NODES` | JSON trust list | must include source peers |
| `POCP_REQUIRE_IMPORT_SIGNATURE` | `true` | `true` |
| `POCP_VERIFY_REMOTE_LEDGER` | `true` | `true` |
| `POCP_FEDERATION_SYNC_ON_STARTUP` | optional | recommended `true` |
| `ENABLE_DEV_LOGIN` | `false` in prod | `false` |

### Trust Genesis (example)

After Genesis publishes its public key and API URL:

```json
[
  {
    "node_id": "node-a",
    "base_url": "https://api.genesis.example.com",
    "public_key": "<genesis-public-key-hex>",
    "trust_weight": 0.7
  }
]
```

Set in `backend/.env` as one line or use `backend/config/trusted_nodes.yaml` (if your deployment loads it).

---

## 3. Start stack

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

Use **separate** `POSTGRES_PASSWORD` and volume from Genesis. Do not share database.

---

## 4. Verify federation

```bash
curl -s https://api.your-school.example.com/api/v1/federation/node | jq .
curl -s https://api.your-school.example.com/api/v1/federation/peers/health | jq .
curl -s -X POST https://api.your-school.example.com/api/v1/federation/sync | jq .
```

Cross-node reputation (after import):

```bash
curl -s "https://api.your-school.example.com/api/v1/federation/reputation?portable_id=github:username"
```

---

## 5. Mutual trust (D2)

Genesis operator adds your node to **their** `POCP_TRUSTED_NODES` via PR or env update. Federation is **opt-in both directions** — no global approval authority.

---

## 6. Anti-monopoly checklist

- [ ] Separate legal entity or community operates this VPS
- [ ] `GET /api/v1/ledger/verify` public
- [ ] Daily anchor to git or object storage (see `.github/workflows/ledger-anchor.yml`)
- [ ] Users can export proof packets without operator approval
- [ ] Document your `node_id` and public key for peer operators
