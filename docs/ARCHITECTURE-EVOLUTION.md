# Architecture Evolution — Genesis to Contribution Internet

How PoCP AI Commons evolves from a single-node MVP to a federated **contribution network**. This is the protocol-phase view referenced from [ARCHITECTURE.md](./ARCHITECTURE.md) and [ROADMAP.md](../ROADMAP.md).

---

## Phase map

| Phase | Focus | Trust model |
|-------|--------|-------------|
| **0 — Genesis** | Narrative, schema, demo loop | Single operator |
| **1 — Genesis MVP** | Entity loop, wallet, AI chat, verify | Advisory witnesses + optional manual finalize |
| **2 — Entity-equal automation** | Policy auto-finalize, issuance caps | Witness quorum + traceable delegate |
| **3 — Verify-don't-trust layer** | Hash chain, Merkle anchors, graph SPV, offline audit | Independent replay; federation cosign |
| **4 — Federation** | Portable proof import, peer mirror, partial reputation | Trusted-node market; hybrid crypto suite |
| **5 — Distributed intelligence** | StudyAgent, MCP/A2A, capability receipts | Multi-Entity invocation traces |
| **6 — Contribution Internet** | Many nodes, graph memory, open finalization policy versions | Peers choose policy; no global human gate |

Current codebase spans **phases 1–5** in various maturity levels.

---

## Layered architecture (target)

```text
┌─────────────────────────────────────────────────────────┐
│  Experience — React dashboard, proof export, audit CLI    │
├─────────────────────────────────────────────────────────┤
│  Protocol API — contributions, finalize, graph, ledger    │
├─────────────────────────────────────────────────────────┤
│  Policy — finalization_policy.yaml, issuance_budget, abuse │
├─────────────────────────────────────────────────────────┤
│  Witness layer — OpenAI / DeepSeek / Ollama / Mock        │
├─────────────────────────────────────────────────────────┤
│  Memory — ledger chain · graph Merkle · proof packets     │
├─────────────────────────────────────────────────────────┤
│  Federation — import, cosign, crypto readiness, mirror    │
└─────────────────────────────────────────────────────────┘
```

---

## Finalization evolution

**Early pilot (deprecated as default):** Human Reviewer clicks approve after AI verify.

**Current default ([ENTITY-EQUALITY.md](./ENTITY-EQUALITY.md)):**

```text
Submit → multi-witness verify → policy verdict → auto-finalize → ledger + CP/BC
```

Any Entity type may finalize when instance policy assigns a delegate. Humans are not a protocol privilege.

---

## Memory evolution

| Stage | Mechanism | Bitcoin-inspired parallel |
|-------|-----------|---------------------------|
| v0.1 | Append-only `ledger_records` | Block chain |
| v0.1+ | `prev_hash` / `record_hash` | Header linkage |
| v0.1+ | `/ledger/anchor` Merkle root | Merkle root in block |
| v0.1+ | `graph_merkle_root` in anchor | UTXO-style relationship graph |
| v0.2 | Hybrid signatures (Ed25519 + ML-DSA) | — (PoCP-specific federation trust) |
| v0.3 | SHA-3 hash agility on new rows | Algorithm upgrade without rewrite |

See [inspiration-mappings/bitcoin.md](./inspiration-mappings/bitcoin.md) and [QUANTUM-READINESS.md](./QUANTUM-READINESS.md).

---

## Federation evolution

1. **Export** — `GET /contributions/{id}/proof` (portable packet)
2. **Verify offline** — `POST /proof/verify`, `verify_standalone.py`
3. **Mirror node** — read-only audit via `audit_node.py remote`
4. **Import** — partial reputation on trusted proof (`federation/import`)
5. **Cosign** — peer attestations on shared anchor hash

Details: [PORTABLE-PROOF-FEDERATION.md](./PORTABLE-PROOF-FEDERATION.md) · [deploy/FEDERATION-SECOND-NODE.md](../deploy/FEDERATION-SECOND-NODE.md)

---

## Non-goals (unchanged)

- No token-first economics in protocol core ([NO-TOKEN-FIRST.md](../NO-TOKEN-FIRST.md))
- No mandatory blockchain or DAO for MVP finalization
- No permanent human-only gate in protocol spec

---

## Related docs

- [NATIVE-TECHNOLOGY-PRINCIPLES.md](./NATIVE-TECHNOLOGY-PRINCIPLES.md)
- [PROTOCOL.md](./PROTOCOL.md)
- [CORE-TECH-STACK.md](./CORE-TECH-STACK.md)
