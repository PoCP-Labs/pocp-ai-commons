# Portable Proof & Federation

How PoCP moves **verified contribution memory** between nodes without requiring a central operator. External narrative: contribution infrastructure — not crypto/Web3.

See also: [FEDERATION-v0.1.md](./FEDERATION-v0.1.md) (when published) · [CONTRIBUTION-PROOF-PACKET-v0.1.md](./CONTRIBUTION-PROOF-PACKET-v0.1.md) · [ENTITY-EQUALITY.md](./ENTITY-EQUALITY.md)

---

## Portable proof packet

A contribution proof is a self-contained JSON document exportable from any node:

```http
GET /api/v1/contributions/{id}/proof
```

Key sections:

| Section | Purpose |
|---------|---------|
| `contribution` | Event metadata, evidence, status |
| `verification` | Witness scores, consensus, policy verdict |
| `integrity` | Canonical hash, crypto suite, hash algorithm |
| `ledger_inclusion` | SPV path into ledger Merkle root |
| `graph_merkle_inclusion` | SPV path into collaboration graph |
| `federation` | Node signatures (classic + optional PQC hybrid) |

Offline verification:

```bash
python backend/scripts/audit_node.py proof --file proof.json
curl -X POST http://localhost:8000/api/v1/proof/verify -d @proof.json
```

---

## Federation trust model

Federation is **opt-in trust between nodes**, not global consensus mining.

1. **Publisher node** — origin of contribution, signs proof and anchor
2. **Consumer node** — imports proof if publisher is in `POCP_TRUSTED_NODES`
3. **Mirror / audit node** — read-only; verifies chain + anchor without mutating state

```bash
python backend/scripts/audit_node.py remote --url https://peer.example.com
python backend/scripts/run_phase_a_acceptance.py http://127.0.0.1:8100 --federation http://127.0.0.1:8101
```

---

## Anchor & cosign

`GET /api/v1/ledger/anchor` publishes:

- `merkle_root` — ledger records commitment
- `graph_merkle_root` — collaboration graph commitment
- `ledger_valid` — local chain verify result
- `peer_attestations` — optional federated cosignatures (`ENABLE_ANCHOR_COSIGN`)

Peers that share the same anchor hash have aligned **public memory** without sharing a database.

---

## Crypto suite negotiation

Nodes advertise readiness:

```http
GET /api/v1/crypto/readiness
```

Federation import may reject proofs below `POCP_MIN_CRYPTO_SUITE`. Hybrid suite (`pocp-crypto-v0.2-hybrid`) adds ML-DSA alongside Ed25519.

See [QUANTUM-READINESS.md](./QUANTUM-READINESS.md).

---

## Import flow (high level)

```text
Node A: submit → verify → finalize → export proof
Node B: POST /federation/import/proof → validate signatures + SPV → partial reputation edge
```

Import does **not** require human approval on Node B — policy on the importing node decides acceptance.

---

## Operator checklist

- [ ] Configure `POCP_NODE_ID`, signing keys, trusted peers
- [ ] Enable anchor cosign for multi-operator demos
- [ ] Run `federation_demo_test.py` or Phase A acceptance with `--federation`
- [ ] Re-sign legacy proofs after crypto suite upgrade: `scripts/resign_proofs.py`

---

## Related

- [inspiration-mappings/bitcoin.md](./inspiration-mappings/bitcoin.md) — verify-don't-trust mapping
- [deploy/FEDERATION-SECOND-NODE.md](../deploy/FEDERATION-SECOND-NODE.md)
- `docker-compose.federation.yml`
