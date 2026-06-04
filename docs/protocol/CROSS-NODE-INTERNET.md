# Cross-Node over the Public Internet

PoCP does **not** run a separate physical network. Each node is a normal HTTPS API (`BACKEND_URL`) reachable over the **existing Internet** — LAN, VPS, or cloud, as long as peers can open TCP to each other’s URL.

Related: [ENTITY-DIALOGUE-PROTOCOL.md](./ENTITY-DIALOGUE-PROTOCOL.md) · [PROTOCOL-EVENT-NETWORK.md](./PROTOCOL-EVENT-NETWORK.md) · [ENTITY-AS-NODE-MODEL.md](./ENTITY-AS-NODE-MODEL.md)

---

## 1. What works today over public URLs

| Capability | Mechanism | Routable via |
|------------|-----------|--------------|
| Peer connect / discover | `POST /federation/peers/connect`, `auto-discover` | probe + addrbook |
| Federation proof pull | `GET {peer}/api/v1/contributions/{id}/proof` | trusted (recommended) |
| Federation overlay relay | `POST {peer}/api/v1/federation/overlay/relay` | trusted |
| Overlay gossip | `POST {peer}/.../overlay/gossip/receive` | trusted |
| **Cross-node dialogue** | `POST {peer}/api/v1/federation/dialogue` | **trusted OR discovered_peer** |
| Mirror remote entities | `POST /federation/peers/{id}/mirror-entities` | discovered + trusted |
| UI / metered execute | `POST {local}/api/v1/intelligence/dialogue` | User JWT on **your** node |

Node A’s browser talks to Node A with login. Node A’s backend talks to Node B over HTTPS using **runtime peer resolution** (`trusted_nodes.yaml` / `POCP_TRUSTED_NODES` first, then `discovered_peer` in DB with healthy addrbook score).

**Protocol manifest:** `GET /api/v1/intelligence/protocol/federation` — schema `pocp.federation_protocol_manifest.v0.1`; lists addrbook summary, feature flags, promotion policy, `/pocp/*` endpoints, and `federation_exchange_import` (see [FEDERATION-PROTOCOL-MANIFEST.md](./FEDERATION-PROTOCOL-MANIFEST.md)).

---

## 2. Two-machine setup (minimal)

### Path A — Fast connect (no trust file edit)

On Node A:

```env
BACKEND_URL=http://localhost:8008
POCP_NODE_ID=node-a
POCP_DIALOGUE_PEER_ROUTE=true
POCP_PEER_AUTO_DISCOVER=true
```

```http
POST /api/v1/federation/peers/connect
{"base_url": "http://192.168.1.50:8100", "mirror_entities": true}
```

### Path B — Explicit trust

### Node B (peer — e.g. VPS `https://api-b.example.com:8100`)

```env
BACKEND_URL=https://api-b.example.com:8100
POCP_NODE_ID=node-b
```

- Open firewall **TCP** on the API port (or 443 behind nginx).
- Register skills/agents; note `portable_id` in entity metadata (or entity UUID).

### Node A (your laptop — e.g. `https://home.example.com:8008` or tunnel)

```env
BACKEND_URL=https://home.example.com:8008
POCP_NODE_ID=node-a
POCP_DIALOGUE_PEER_ROUTE=true
POCP_TRUSTED_NODES=[{"node_id":"node-b","base_url":"https://api-b.example.com:8100","trust_weight":0.9}]
```

Symmetric trust on B (optional, for gossip / return traffic):

```env
POCP_TRUSTED_NODES=[{"node_id":"node-a","base_url":"https://home.example.com:8008","trust_weight":0.9}]
```

### Health check from A

```bash
curl -s https://api-b.example.com:8100/health
curl -s https://api-b.example.com:8100/api/v1/federation/node
```

---

## 3. Cross-node `invoke` (dialogue)

Set **`to.node_id`** to the peer’s `POCP_NODE_ID`. Use **`portable_id`** (or an entity id that exists on B) for the target skill/agent.

**Via mirrored entity (recommended):** select local mirror `entity_id` in UI; routing rewrites `to` automatically.

**Explicit envelope:**

```json
{
  "schema": "pocp.entity_dialogue.v0.1",
  "dialogue_id": "dlg_cross_1",
  "kind": "invoke",
  "from": { "entity_id": "<human-on-A>", "node_id": "node-a" },
  "to": { "portable_id": "pocp:node-b:skill:remote-tutor", "node_id": "node-b" },
  "payload": {
    "route_peer": true,
    "input": "Explain PoCP cross-node routing",
    "execute": false
  }
}
```

POST to **Node A**: `/api/v1/intelligence/dialogue` (with user JWT).

Routing:

1. A validates envelope; sees `to.node_id=node-b` ≠ local.
2. A resolves peer via trust list or discovered_peer (`probe_base_url`).
3. A forwards to `https://api-b.../api/v1/federation/dialogue`.
4. B runs invoke locally; response returns to A (with `result.peer_route: true`).

Force route even if a stale local copy of the entity exists: `"route_peer": true`.  
Disable: `"route_peer": false` or omit `to.node_id`.

**Quote → invoke (exchange spine):** run `kind: quote` first on A (routed to B); pass `refs.exchange_id` into invoke `refs` on B for metered settlement alignment.

---

## 4. Security notes (pilot)

- **Discovered peers** may receive federation dialogue after successful probe; banned peers (`peer_addrbook.banned`) are rejected.
- **Import / gossip** still prefer trusted or promoted peers.
- Use **HTTPS** in production (`BACKEND_URL=https://...`).
- Optional hardening (roadmap): peer HMAC header, mTLS, proof signatures on gossip.
- Do not expose Postgres or admin ports publicly — only the API.

---

## 5. Troubleshooting

| Symptom | Check |
|---------|--------|
| `to.node_id X not routable` | Connect peer or add trust; check addrbook ban |
| `Untrusted source_node_id` | B’s trust list must include A’s `POCP_NODE_ID` (gossip) |
| `peer dialogue failed: Connection refused` | Firewall, `BACKEND_URL`, wrong port, Docker use `probe_base_url` |
| `target entity not found` on B | Skill exists on B; mirror entities or use `portable_id` |
| Works on LAN, fails on WAN | NAT: use public IP/DNS in `base_url`, not `127.0.0.1` |
| Execute fails cross-node | `execute: true` runs on **peer**; peer needs LLM credits / mock provider |
| Docker localhost peers empty | Set `POCP_PEER_DISCOVERY_HOST=host.docker.internal` |

---

## 6. Env reference

| Variable | Purpose |
|----------|---------|
| `BACKEND_URL` | This node’s public base URL (advertised in federation manifest) |
| `POCP_NODE_ID` | Logical node id in dialogue `from` / `to` |
| `POCP_TRUSTED_NODES` | JSON list of `{node_id, base_url, trust_weight}` |
| `POCP_DIALOGUE_PEER_ROUTE` | `true` — forward dialogue to peer `to.node_id` |
| `POCP_PEER_DISCOVERY_SEEDS` | Seed URLs for auto-discover |
| `POCP_PEER_BOOTSTRAP_URL` | DNS-seed JSON URL (see `backend/config/pocp-bootstrap.example.json`) |
| `POCP_PEER_ADDR_RELAY` | Pull `known_peers` from connected manifests |
| `POCP_PEER_AUTO_PROMOTE` | Promote high-score peers to `trusted_nodes.yaml` |
| `POCP_PEER_DIALOGUE_TIMEOUT` | HTTP timeout seconds (default 120) |
| `POCP_OVERLAY_GOSSIP` | Push sealed batches to peers after seal (optional) |
