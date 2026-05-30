# Openness and Anti-Monopoly

**How PoCP stays public infrastructure — and what private deployment can and cannot capture.**

PoCP AI Commons is designed so that **no person, company, group, or nation owns the protocol**. Anyone may download, run, fork, and audit the system. This document explains the legal boundary (MIT License), the architectural boundary (protocol vs instance), and the practical safeguards that limit single-operator capture.

See also: [VISION.md](./VISION.md) · [PROTOCOL.md](./PROTOCOL.md) · [FEDERATION-v0.1.md](./FEDERATION-v0.1.md) · [FEDERATION-HARDENING.md](./FEDERATION-HARDENING.md) · [PROTOCOL-SPEC-v0.1.md](../PROTOCOL-SPEC-v0.1.md)

---

## 1. Three layers — what “belongs to humanity” means

| Layer | What it is | Who can “own” it | How everyone participates |
|-------|------------|------------------|---------------------------|
| **Protocol** | PoCP spec, proof packets, ledger semantics, portable identity | Nobody exclusively — it is a public specification | Read and implement without logging into any server |
| **Implementation** | This open-source repository (API, UI, verifiers, federation code) | Forkable under MIT; copyright notice must be preserved | `git clone`, modify, deploy anywhere |
| **Instance** | One running node (one Postgres, one domain, one operator) | Whoever operates that server is responsible for **that instance only** | Users register, contribute, earn AI Credits on that node |

**Genesis is one instance, not the whole network.** Rain’s node records the founding loop and demo seed; it is a starting point, not a mandatory central gate.

```text
Protocol (public spec)     →  not owned by any operator
Implementation (open code) →  MIT — forkable by anyone
Instance (one server)      →  operated locally; one node among many
```

---

## 2. Legal openness — MIT License

PoCP AI Commons is released under the [MIT License](../LICENSE).

**Permitted without asking permission:**

- Download and run privately or on the public internet
- Modify the code and deploy your own branded instance
- Use commercially
- Keep modifications closed-source (MIT does not require you to publish forks)

**Required:**

- Include the MIT copyright and license notice in copies or substantial portions of the Software

**What MIT does *not* grant:**

- Ownership of the PoCP **name** beyond normal trademark law (not covered by the software license)
- Control over **other people’s nodes**, ledgers, or signed proofs
- The right to claim you invented the **protocol specification** if you only run a fork

MIT optimizes for **adoption and experimentation**. It deliberately does **not** legally forbid a walled-garden deployment. Anti-monopoly is enforced mainly by **architecture, verifiability, and federation** — not by a copyleft license.

---

## 3. Can someone deploy privately and “take it for themselves”?

**Short answer:** They can run **their own instance**. They cannot privately own **PoCP as a protocol**, the **genesis ledger of the public network**, or **recognition across nodes they do not trust**.

### 3.1 What a private operator *can* control

| Asset | Notes |
|-------|-------|
| Their server and database | Users on that instance depend on that operator for uptime and policy |
| Local tasks, wallets, AI Credits pool | Funded and governed on that node |
| UI branding of a fork | e.g. rename the product while keeping MIT notice |
| Who may register or review | Instance-level access control |

A fully closed deployment (no federation, no public ledger APIs) behaves like a **private SaaS built on PoCP code** — not like ownership of PoCP itself.

### 3.2 What they *cannot* capture (if the public design is used)

| Public good | Why it stays outside one operator |
|-------------|-----------------------------------|
| Protocol specification | Published in [PROTOCOL-SPEC-v0.1.md](../PROTOCOL-SPEC-v0.1.md); anyone can implement independently |
| Verifiable contribution history | Hash-chained ledger + signed proof packets |
| Cross-node reputation | Opt-in trust via `POCP_TRUSTED_NODES`; no central approval |
| Portable identity | `portable_id` (e.g. `github:username`) aligns entities across nodes |
| Third-party audit | `GET /api/v1/ledger/verify`, `/ledger/export`, `/ledger/anchor` without DB access |
| Parallel nodes | Communities, schools, and labs can run separate instances |

Other nodes **do not automatically trust** a private kingdom. Reputation imported from an untrusted or unknown node has no weight unless peers configure trust.

---

## 4. Architectural anti-monopoly mechanisms

These are the engineering counterweights to single-operator capture:

### 4.1 Verifiable ledger memory

Each ledger record links to the previous via SHA-256 (`prev_hash`, `record_hash`). Anyone can call:

```http
GET /api/v1/ledger/verify
```

Tampering breaks the chain detectably. Operators cannot silently rewrite history without leaving evidence — **if** users and peers actually verify.

### 4.2 Portable contribution proofs

Approved contributions can be exported as **Contribution Proof Packets** with:

- `content_hash` (evidence integrity)
- `integrity.proof_hash`
- Optional **Ed25519** `federation.signature` from the source node

Proofs can be stored offline, mirrored, and checked without trusting the operator’s UI.

See [CONTRIBUTION-PROOF-PACKET-v0.1.md](./CONTRIBUTION-PROOF-PACKET-v0.1.md) and [PORTABLE-PROOF-FEDERATION.md](./PORTABLE-PROOF-FEDERATION.md).

### 4.3 Federation — trust is explicit, not centralized

Each node declares trusted peers (YAML or `POCP_TRUSTED_NODES`). Import rules (v0.2+):

- Verify remote ledger before import (`POCP_VERIFY_REMOTE_LEDGER`)
- Optionally require signatures (`POCP_REQUIRE_IMPORT_SIGNATURE`)
- Merge **reputation** from trusted nodes; **AI Credits remain local** per node

```http
GET  /api/v1/federation/node
GET  /api/v1/federation/peers/health
POST /api/v1/federation/sync
```

No global “PoCP Inc.” must bless a node. Trust is **configured by each community**.

See [FEDERATION-DEMO.md](./FEDERATION-DEMO.md) for a two-node local demo.

### 4.4 Public anchors

Daily or manual anchor files (Merkle root of the ledger tip) can be committed to git under `anchors/` or fetched remotely:

```bash
python backend/scripts/fetch_anchor.py https://api.example.com ../anchors
```

Third parties can reconcile anchors **without** database access or operator goodwill.

### 4.5 Read-only mirror mode

A node can run as `POCP_NODE_MODE=read_only_mirror`: no local contribution writes, only sync/import from trusted sources. Mirrors reduce “only one canonical server” pressure.

---

## 5. Guidance for users — avoid lock-in

| Practice | Why |
|----------|-----|
| Prefer nodes that expose `ledger/verify` and periodic anchors | History is auditable |
| Export your proof packets after approval | You hold cryptographic evidence independent of the UI |
| Use OAuth identities that map to stable `portable_id` | Reputation can follow across federated nodes |
| Check whether a node participates in federation you trust | Isolated nodes = operator-dependent reputation |
| Run or support a **second independent node** | The strongest anti-monopoly move is plural operators |

If an operator shuts down, changes rules arbitrarily, or runs a black box, users with exported proofs and peers who verify signatures retain **evidence**; users who never exported depend entirely on that operator.

---

## 6. Guidance for operators — run a node, don’t capture the network

**Good citizenship:**

- Publish HTTPS API with verify/export/anchor endpoints
- Document your `node_id` and public key; register in community trust lists
- Sync with or mirror at least one other independent operator
- Commit or publish ledger anchors
- Keep `ENABLE_DEV_LOGIN=false` on the public internet; use GitHub OAuth

**Red flags (for users and peer nodes):**

- No ledger verify API
- No export or proof endpoints
- Refusal to sign proofs
- Single operator claiming to be the “official” entire PoCP network
- Opaque rule changes with no ledger events

---

## 7. Honest limits — what we cannot promise yet

PoCP is in **Genesis / Sprint Alpha**. Anti-monopoly is **directional**, not finished:

| Gap | Current state | Direction |
|-----|---------------|-----------|
| Single popular domain | One demo instance may dominate early | Multi-node federation + community deploy guides |
| Trust list changes | Often env/YAML + maintainer | Governance proposals logged to ledger (roadmap) |
| MIT allows closed forks | Legal | Social + federated recognition makes walled gardens less useful |
| AI Credits | Always local per node | By design — prevents one pool being “the currency of PoCP” |
| Trademark / naming | Not fully specified in repo | Community policy may clarify “PoCP AI Commons” vs forks |

**Maintainers will exist for a while** (merging PRs, Genesis guidance). The goal is to move **protocol memory, reputation, and audit** toward many verifiable nodes and public anchors — not toward eternal dependence on one server.

---

## 8. FAQ

### Can I fork and run PoCP inside my company without sharing changes?

**Yes**, under MIT, as long as you include the license notice.

### Does that mean my company “owns PoCP”?

**No.** You operate an instance. You do not own the protocol spec, other nodes’ data, or federation trust unless peers choose to trust you.

### Can a fork pretend to be the only real PoCP?

They can misrepresent in marketing; they **cannot** force other nodes to accept their ledger or reputation without trust configuration. Users should verify anchors and node keys.

### Is a private deployment against the spirit of PoCP?

A closed silo conflicts with **contribution internet** goals. A **private pilot** that later federates and publishes verify APIs is a reasonable on-ramp.

### Would AGPL or another license be better?

MIT maximizes forks and deployments. Copyleft would require sharing modifications but would **not** stop private instances. License choice is a governance tradeoff; today the project uses **open code + verifiable federation** as the primary anti-monopoly strategy.

---

## 9. Related documents

| Document | Topic |
|----------|-------|
| [PUBLIC-DEPLOY.md](./PUBLIC-DEPLOY.md) | Run a public community instance |
| [FEDERATION-v0.1.md](./FEDERATION-v0.1.md) | Multi-node recognition model |
| [FEDERATION-HARDENING.md](./FEDERATION-HARDENING.md) | From single operator to distributed trust |
| [PROTOCOL-SPEC-v0.1.md](../PROTOCOL-SPEC-v0.1.md) | Builder-facing protocol contract |
| [Genesis (zh-CN)](./genesis/zh-CN.md) | Founding statement and principles |

---

## 10. Summary

> **Anyone may deploy their own node. No one may privately own PoCP as a protocol, the public contribution memory, or cross-network recognition.**

Private deployment is allowed and expected. Capture is limited when the network uses **verifiable ledgers, signed proofs, explicit federation trust, portable identity, and many independent operators**. That is how “open to all humanity” becomes engineering reality — not merely a slogan.
