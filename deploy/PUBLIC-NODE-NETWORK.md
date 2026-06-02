# PoCP Public Node Network

How to run PoCP as a real public node network instead of a localhost federation demo.

This guide assumes:

- each node runs on its own VPS or cloud VM;
- each node has its own domain or subdomain;
- each node has its own Postgres database and private keys;
- federation trust is explicit and per-node;
- TLS is terminated by Caddy or Nginx on the host.

---

## 1. The target shape

For a distributed public network, each operator should run an independent stack:

```text
Internet
  |
  | HTTPS
  v
Caddy / Nginx on VPS
  |
  +--> app.example.org  -> frontend container (127.0.0.1:3000)
  |
  +--> api.example.org  -> backend container  (127.0.0.1:8008)
                              |
                              +--> Postgres container (private only)
```

Then nodes federate with each other over public HTTPS:

```text
Node A <--> Node B <--> Node C
   \           |           /
    \------ optional trust links ------/
```

PoCP today is not a permissionless gossip mesh. It is a **signed, trust-listed federation**:

- each node publishes a public identity;
- each node exposes public verification endpoints;
- each node chooses which peers it trusts;
- imports and sync happen only from configured trusted peers.

---

## 2. Node roles

Use one of these roles per deployment:

### Full node

Use when the operator wants to:

- accept local writes;
- host local entities and capabilities;
- publish proofs and ledger state;
- import from other trusted nodes.

Recommended settings:

```env
POCP_NODE_MODE=full
POCP_REQUIRE_IMPORT_SIGNATURE=true
POCP_VERIFY_REMOTE_LEDGER=true
POCP_FEDERATION_SYNC_ON_STARTUP=false
```

### Read-only mirror / audit node

Use when the operator wants to:

- verify public state independently;
- mirror trusted peers;
- provide public auditability;
- avoid local writes.

Recommended settings:

```env
POCP_NODE_MODE=read_only_mirror
POCP_REQUIRE_IMPORT_SIGNATURE=true
POCP_VERIFY_REMOTE_LEDGER=true
POCP_FEDERATION_SYNC_ON_STARTUP=true
```

---

## 3. Bring up one public node

### Step A. Prepare DNS

Point these records to the server:

- `api.node-a.example.com`
- `app.node-a.example.com`

### Step B. Generate unique node keys

On the server:

```bash
python backend/scripts/generate_node_keys.py node-a
```

Save:

- `POCP_NODE_ID`
- `POCP_NODE_PRIVATE_KEY`
- `POCP_NODE_PUBLIC_KEY`

Never reuse keys across nodes.

### Step C. Create production env files

Project root `.env`:

```env
POSTGRES_PASSWORD=replace-with-strong-secret
VITE_API_URL=https://api.node-a.example.com
```

`backend/.env`:

```env
APP_ENV=production
BACKEND_URL=https://api.node-a.example.com
FRONTEND_URL=https://app.node-a.example.com
JWT_SECRET=replace-with-strong-secret
DATABASE_URL=postgresql+psycopg://pocp:replace-with-strong-secret@postgres:5432/pocp

POCP_NODE_ID=node-a
POCP_NODE_PRIVATE_KEY=...
POCP_NODE_PUBLIC_KEY=...

POCP_NODE_MODE=full
POCP_REQUIRE_IMPORT_SIGNATURE=true
POCP_VERIFY_REMOTE_LEDGER=true
POCP_FEDERATION_SYNC_ON_STARTUP=false

ENABLE_DEV_LOGIN=false
ENABLE_MOCK_VERIFIER=false
```

### Step D. Start the stack

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.public-node.yml up -d --build
```

This starts:

- frontend on `127.0.0.1:3000`
- backend on `127.0.0.1:8008`
- postgres private to Docker network

### Step E. Expose it through Caddy

Use [`deploy/Caddyfile.example`](./Caddyfile.example) as the base:

```caddy
api.node-a.example.com {
	reverse_proxy localhost:8008
}

app.node-a.example.com {
	reverse_proxy localhost:3000
}
```

Then reload Caddy.

---

## 4. What every public node must expose

These endpoints should be reachable from the public internet over HTTPS:

- `GET /.well-known/pocp-node.json`
- `GET /health`
- `GET /api/v1/federation/node`
- `GET /api/v1/federation/trust`
- `GET /api/v1/federation/peers/health`
- `GET /api/v1/ledger/verify`
- `GET /api/v1/ledger/anchor`

These are the minimum operator-facing checks:

```bash
curl -s https://api.node-a.example.com/.well-known/pocp-node.json
curl -s https://api.node-a.example.com/api/v1/federation/node
curl -s https://api.node-a.example.com/api/v1/ledger/verify
curl -s https://api.node-a.example.com/api/v1/federation/trust
```

---

## 5. Connect nodes into a public network

### Step A. Exchange public metadata

Each operator publishes:

- node ID
- API base URL
- Ed25519 public key
- optional PQC public key

### Step B. Add trusted peers

Example `backend/config/trusted_nodes.yaml`:

```yaml
spec_version: "0.1"
trusted_nodes:
  - node_id: node-b
    base_url: https://api.node-b.example.com
    public_key: "<node-b-ed25519-public-key>"
    pqc_public_key: "<optional-node-b-pqc-public-key>"
    trust_weight: 0.8
  - node_id: node-c
    base_url: https://api.node-c.example.com
    public_key: "<node-c-ed25519-public-key>"
    trust_weight: 0.6
```

Validate locally:

```bash
python backend/scripts/validate_trusted_nodes.py backend/config/trusted_nodes.yaml
```

### Step C. Probe the network

After restart:

```bash
curl -s https://api.node-a.example.com/api/v1/federation/peers/health
curl -s -X POST https://api.node-a.example.com/api/v1/federation/sync
```

---

## 6. Recommended bootstrap topology

For the first real public network, keep it simple:

### Topology 1. Hub with independent mirrors

```text
Genesis full node
  |
  +--> University node (full)
  +--> Community node (full)
  +--> Audit mirror A
  +--> Audit mirror B
```

Good for first launch because:

- easiest to debug;
- clearest trust relationships;
- mirrors improve auditability quickly.

### Topology 2. Mutual federation ring

```text
Node A <-> Node B <-> Node C <-> Node A
```

Good after basics are stable because:

- no single sync source;
- more resilient public verification;
- better reputation portability story.

Avoid jumping straight to a dense full mesh before operator procedures are stable.

---

## 7. Production checklist

- [ ] One VPS per node operator
- [ ] One Postgres instance per node
- [ ] One unique keypair per node
- [ ] HTTPS enabled with public DNS
- [ ] `ENABLE_DEV_LOGIN=false`
- [ ] `ENABLE_MOCK_VERIFIER=false`
- [ ] `/.well-known/pocp-node.json` public
- [ ] `GET /api/v1/ledger/verify` public
- [ ] Trusted peers configured with real HTTPS URLs
- [ ] `federation/peers/health` green
- [ ] At least one independent mirror node online

---

## 8. Recommended first rollout

1. Bring up Node A as the first public full node.
2. Bring up Node B as a read-only mirror trusting Node A.
3. Run public verification and sync checks.
4. Bring up Node C as a second full node with its own operator.
5. Add mutual trust gradually instead of enabling every edge at once.

That gets you to a real distributed node network with the fewest moving parts.
