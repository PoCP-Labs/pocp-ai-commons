# Threat Model v0.1

**Scope:** PoCP neural base (exchange spine + three chains + federation)

---

## 1. Assets

| Asset | Chain | Impact if compromised |
|-------|-------|------------------------|
| GRC ledger integrity | Memory | Forged rights, double-spend |
| Graph Merkle | Structure | Hidden collaboration, false attribution |
| Exchange receipts | Signal | Unpaid compute, fake usage |
| Witness attestations | Signal | Bad contributions finalized |
| Entity keys / manifests | Neuron | Impersonation, rogue providers |
| Anchor cosignatures | Memory | Undetected history rewrite |
| Federation trust config | Federation | Poisoned import |

---

## 2. Adversaries

| Actor | Goal | Capability |
|-------|------|------------|
| **Malicious consumer** | Use compute without paying | API abuse, replay old quotes |
| **Malicious provider** | Bill without delivering | Fake receipts, inflated usage |
| **Rogue witness** | Pass bad contributions | Low-quality or bought scores |
| **Insider operator** | Mint unearned CP/BC | DB access, skip ledger |
| **Federation impostor** | Import fake proofs | Spoofed instance, weak trust |
| **Sybil farmer** | Harvest CP via fake Entities | Many low-cost identities |

---

## 3. Controls (mapped)

| Threat | Control | Constitution | Status |
|--------|---------|--------------|--------|
| Unpaid compute | Quote + atomic settlement + receipt hash | Art. II | Partial — need `ledger_record_id` FK |
| Fake receipt | Receipt hash in ledger + proof verify | Art. II, VI | ✅ capability_receipt |
| Ledger rewrite | Hash chain + anchor + external audit | Art. I | ✅ ledger_chain |
| Balance drift | Wallet replay audit | Art. I.4 | ✅ wallet_audit |
| Witness collusion | Multi-witness quorum + distinct Entities | Art. III.10, IV.14 | Partial |
| Self-finalize abuse | Policy + audit flag | Art. III.12 | ✅ policy engine |
| Rogue import | L0–L3 levels + crypto floor | Art. V | Partial |
| Sybil | Rate limits, risk_level, community trust | — | Partial anti_abuse |
| Operator mint | issuance_budget + constitution CI | Art. I.5 | Planned tests |

---

## 4. Trust boundaries

```text
┌─────────────────────────────────────────┐
│  Untrusted: client apps, remote peers    │
└──────────────────┬──────────────────────┘
                   │ signed requests, proofs
┌──────────────────▼──────────────────────┐
│  Instance API (verify before trust)      │
└──────────────────┬──────────────────────┘
                   │
┌──────────────────▼──────────────────────┐
│  GRC + graph (strong consistency)        │
└──────────────────┬──────────────────────┘
                   │ SPV / export
┌──────────────────▼──────────────────────┐
│  External auditor (audit_node, wallet)   │
└─────────────────────────────────────────┘
```

**Never trust:** client-reported usage, unverified federation payloads, witness scores without `witness_entity_id`.

**Verify first:** ledger chain, wallet replay, proof packet, manifest signature.

---

## 5. Residual risks (accepted v0.1)

| Risk | Mitigation path |
|------|-----------------|
| Single-instance DB tampering before anchor | External anchor cosigners, mirror audit |
| LLM witness nondeterminism | Hash rationale, freeze attest snapshot |
| Heuristic ledger↔tx link | Replace with FK `ledger_record_id` |
| No global Sybil resistance | Community-scoped trust, not one global ID |

---

## 6. Security test requirements

Add to CI (`test_constitution.py`):

1. Settlement without ledger row → must fail
2. Credit tx sum ≠ wallet balance → audit fails
3. Proof without `exchange_inclusion` for compute path → verify warns
4. Manifest signature invalid → 422 on publish
5. Import below L1 without proof → rejected
