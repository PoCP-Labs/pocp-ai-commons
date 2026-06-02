# Cross-Node over the Public Internet

PoCP does **not** run a separate physical network. Each node is a normal HTTPS API (`BACKEND_URL`) reachable over the **existing Internet** — LAN, VPS, or cloud, as long as peers can open TCP to each other’s URL.

Related: [ENTITY-DIALOGUE-PROTOCOL.md](./ENTITY-DIALOGUE-PROTOCOL.md) · [PROTOCOL-EVENT-NETWORK.md](./PROTOCOL-EVENT-NETWORK.md)

---

## 1. What works today over public URLs

| Capability | Mechanism | Auth on peer call |
|------------|-----------|-------------------|
| Federation proof pull | `GET {peer}/api/v1/contributions/{id}/proof` | Trust list only |
| Federation overlay relay | `POST {peer}/api/v1/federation/overlay/relay` | Trust + local import rules |
| Overlay gossip | `POST {peer}/api/v1/intelligence/network/overlay/gossip/receive` | Trust list (`source_node_id`) |
| **Cross-node dialogue** | `POST {peer}/api/v1/federation/dialogue` | Trust list (`to.node_id` + `POCP_TRUSTED_NODES`) |
| UI / metered execute | `POST {local}/api/v1/intelligence/.../dialogue` | User JWT on **your** node only |

Node A’s browser talks to Node A with login. Node A’s backend talks to Node B over HTTPS using the **trusted peer** configuration — no shared user session required.

---

## 2. Two-machine setup (minimal)

### Node B (peer — e.g. VPS `https://api-b.example.com:8100`)

```env
BACKEND_URL=https://api-b.example.com:8100
POCP_NODE_ID=node-b
# Postgres + normal PoCP env…
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

```json
{
  "schema": "pocp.entity_dialogue.v0.1",
  "dialogue_id": "dlg_cross_1",
  "kind": "invoke",
  "from": { "entity_id": "<human-on-A>", "node_id": "node-a" },
  "to": { "portable_id": "skill:remote-tutor", "node_id": "node-b" },
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
2. A forwards to `https://api-b.../api/v1/federation/dialogue`.
3. B runs invoke locally; response returns to A (with `result.peer_route: true`).

Force route even if a stale local copy of the entity exists: `"route_peer": true`.  
Disable: `"route_peer": false` or omit `to.node_id`.

---

## 4. Security notes (pilot)

- Only nodes in **`POCP_TRUSTED_NODES`** may receive federation dialogue / gossip.
- Use **HTTPS** in production (`BACKEND_URL=https://...`).
- Optional hardening (roadmap): peer HMAC header, mTLS, proof signatures on gossip.
- Do not expose Postgres or admin ports publicly — only the API.

---

## 5. Troubleshooting

| Symptom | Check |
|---------|--------|
| `Untrusted source_node_id` | B’s trust list must include A’s `POCP_NODE_ID` |
| `peer dialogue failed: Connection refused` | Firewall, `BACKEND_URL`, wrong port |
| `target entity not found` on B | Skill exists on B; use `portable_id` or correct UUID |
| Works on LAN, fails on WAN | NAT: use public IP/DNS in `base_url`, not `127.0.0.1` |
| Execute fails cross-node | `execute: true` runs on **peer**; peer needs LLM credits / mock provider |

---

## 6. Env reference

| Variable | Purpose |
|----------|---------|
| `BACKEND_URL` | This node’s public base URL (advertised in federation manifest) |
| `POCP_NODE_ID` | Logical node id in dialogue `from` / `to` |
| `POCP_TRUSTED_NODES` | JSON list of `{node_id, base_url, trust_weight}` |
| `POCP_DIALOGUE_PEER_ROUTE` | `true` — forward dialogue to trusted `to.node_id` |
| `POCP_PEER_DIALOGUE_TIMEOUT` | HTTP timeout seconds (default 120) |
| `POCP_OVERLAY_GOSSIP` | Push sealed batches to peers after seal (optional) |
