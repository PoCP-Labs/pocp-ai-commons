# Entity Node Manifest v0.1

**Every Entity is a neuron; every neuron may expose a node facet.**

Servers (Archive, Org) are **hosts** for some Entities — not the definition of network membership.

---

## 1. Node facet vs Entity record

| Layer | Storage | Purpose |
|-------|---------|---------|
| Entity | `entities` table | Identity, type, wallet, reputation |
| Node manifest | JSON doc + optional DB row | What this Entity **offers** to the network |
| ELC | Entity-local chain | What this Entity **participated in** |

An Entity without a manifest is a **passive neuron** (consumer-only).  
An Entity with manifest is an **active neuron** (provider, witness, archive, etc.).

---

## 2. Role taxonomy

| Role | Responsibility | Min manifest fields |
|------|----------------|---------------------|
| **Wallet** | Hold CP/BC, sign spends | `wallet_id`, `entity_id` (implicit) |
| **Witness** | Attest contributions / receipts | `witness_endpoints`, `models[]` |
| **Executor** | Run Agent/Skill invocations | `capabilities[]`, `executor_url` |
| **Capability** | Publish callable surface | `capabilities[]` per CAPABILITY-SCHEMA |
| **Finalizer** | Policy delegate (Entity-equal) | `finalizer_policy_ids[]` |
| **Archive** | GRC read replica, proof export | `archive_url`, `ledger_verify_url` |
| **Mirror** | Read-only federation peer | `mirror_of`, `trust_level` |
| **Audit** | Third-party verify service | `audit_endpoints[]` |
| **Trust** | Community trust registry | `trust_policy`, `accepted_roots[]` |

Roles are **non-exclusive**. One Entity may be Witness + Capability + Archive.

---

## 3. Manifest schema

```json
{
  "protocol": "pocp-node-manifest-v0.1",
  "entity_id": "entity_clarion_0",
  "entity_type": "llm",
  "display_name": "Clarion-0",
  "roles": ["witness", "finalizer"],
  "endpoints": {
    "well_known": "https://node.example/.well-known/pocp-node.json",
    "health": "https://node.example/api/v1/health",
    "capabilities": "https://node.example/api/v1/capabilities",
    "witness": "https://node.example/api/v1/witness/attest"
  },
  "capabilities": [],
  "witness": {
    "models": ["clarion-0"],
    "attestation_pubkey": "base64…",
    "supported_evidence": ["contribution.v0.3", "capability_receipt.v0.1"]
  },
  "crypto": {
    "suite": "pocp-crypto-v1",
    "signing_key_id": "key_…"
  },
  "federation": {
    "instance_id": "pocp-labs-main",
    "trust_level": "L2",
    "accepted_anchor_roots": []
  },
  "updated_at": "2026-05-29T12:00:00Z",
  "signature": {
    "algorithm": "ed25519",
    "value": "base64…"
  }
}
```

**Discovery:**

- Instance API: `GET /api/v1/entities/{entity_id}/node-manifest`
- Well-known: `GET /.well-known/pocp-node.json` (instance default Archive Entity)

---

## 4. Witness attest block (required v0.4)

Verifier attestations stored for finalization **must** include:

```json
{
  "witness_entity_id": "entity_lumen_0",
  "witness_manifest_url": "https://…/node-manifest",
  "score": 0.92,
  "rationale_hash": "sha256:…",
  "signed_at": "2026-05-29T12:00:00Z",
  "signature": { "algorithm": "ed25519", "value": "…" }
}
```

**Gap today:** `verifier_entity_id` sometimes missing or provider-string only — fix in `MultiVerifierService` output path.

---

## 5. ELC — Entity Local Chain v0.1

Each Entity maintains an ordered list of **participation records**:

```json
{
  "elc_version": "0.1",
  "entity_id": "human_001",
  "head_hash": "sha256:…",
  "records": [
    {
      "seq": 42,
      "kind": "exchange_settled | contribution_finalized | witness_attest",
      "ref_id": "ex_abc123",
      "grc_ledger_record_id": "lr_…",
      "spv": {
        "ledger_merkle_proof": ["…"],
        "anchor_id": "anchor_…"
      },
      "prev_hash": "…",
      "record_hash": "…"
    }
  ]
}
```

**Rules:**

- ELC is a **view**, not a second source of GRC truth.
- Mirror nodes may serve ELC for any Entity they index.
- SPV lets lightweight clients verify participation without full ledger.

**API (planned):**

- `GET /api/v1/entities/{entity_id}/local-chain?limit=50&cursor=…`
- `GET /api/v1/entities/{entity_id}/local-chain/verify`

---

## 6. Implementation plan

| Step | Deliverable |
|------|-------------|
| 1 | Pydantic schema `NodeManifestV01` in `backend/schemas/node_manifest.py` |
| 2 | `GET /entities/{id}/node-manifest` — synthesize from Entity + capabilities + config |
| 3 | Sign manifest with instance Archive key |
| 4 | `EntityLocalChainService` — append on settlement/finalize hooks |
| 5 | Frontend: Entity profile "Node roles" badge |

---

## 7. Operator vs Entity (mental model)

```text
WRONG:  "Our server is the node; users are accounts inside it."
RIGHT:  "Each Entity is a neuron; our server hosts Archive + some Agent Entities."
```

Documentation and UI should say **Entity** first, **instance/host** second.
