# Federation discovery (CI-5)

Mesh-0 scope: federation peer manifests, public skill node template, and minimum living network steps 3–4 (discover + handshake).

Parent: [MINIMUM-LIVING-NETWORK.md](./MINIMUM-LIVING-NETWORK.md) · Acceptance: `run_phase_a_acceptance.py --federation`

---

## Peer manifest

`GET /api/v1/federation/peers/manifest` returns `pocp.federation_peer_manifest.v0.1`:

- `node_id`, `base_url`, `crypto_suite`, `public_key`
- `trust_policy_bundle_fingerprint` (from active trust policy bundle)
- `handshake` (BI-2 surface: algorithms, challenge endpoint, required headers)
- `well_known` links (`/.well-known/pocp-node.json`, agent card)
- `skill_node_template` embedded reference

Trusted peers: `GET /api/v1/federation/peers/{node_id}/manifest` fetches the same shape live from `POCP_TRUSTED_NODES`.

---

## Minimum living network steps 3–4

| Step | API | Purpose |
|------|-----|---------|
| 3 Discover | `POST /api/v1/federation/peers/discover-capabilities` | Search peer `GET /api/v1/registry/capabilities` |
| 4 Handshake | `POST /api/v1/federation/peers/handshake` | Align trust bundle fingerprint + verify handshake manifest |

Combined handshake (discover + handshake in one call):

```json
POST /api/v1/federation/peers/handshake
{
  "peer_base_url": "http://127.0.0.1:8101",
  "capability_type": "code_review"
}
```

Set `require_trust_bundle_match: true` to fail when bundle fingerprints differ (strict pilots).

---

## Public skill node template

`GET /api/v1/federation/skill-node-template` returns `pocp-skill-node-template.v0.1` — reference roles, default `code_review` capability, and public-node endpoint map for skill providers.

---

## Environment variables

| Variable | Role |
|----------|------|
| `POCP_PEER_DISCOVERY_SEEDS` | JSON list or comma-separated URLs for `POST /federation/peers/auto-discover` |
| `POCP_PEER_COMPUTE_SECRET` | Shared secret for BI-2 HMAC handshake (witness / inference / MCP) |
| `POCP_PEER_HANDSHAKE_MODE` | `shared_secret` (default) or `challenge` |
| `POCP_PEER_HANDSHAKE_TTL_SECONDS` | Nonce TTL (default 300) |
| `POCP_TRUSTED_NODES` | Trusted peer list for mirror / manifest fetch by `node_id` |

---

## Verification

```powershell
python backend/scripts/run_phase_a_acceptance.py http://127.0.0.1:8100 --federation http://127.0.0.1:8101 --skip-optional
cd backend && python -m pytest tests/test_federation_discovery.py -q
```

Federation acceptance runs `federation_peer_manifest` and `federation_peer_handshake` before preflight/demo scripts.

**Docker federation compose:** `POST /peers/handshake` on node A must use a `peer_base_url` reachable from the API container (e.g. `http://backend-b:8000` in `POCP_TRUSTED_NODES`). Host acceptance (`run_phase_a_acceptance.py`) validates manifests and discovery from the runner using published ports (`8100` / `8101`).
