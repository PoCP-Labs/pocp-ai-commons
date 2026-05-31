# Native Technology Principles

What PoCP treats as **first-class protocol technology** vs borrowed patterns vs explicit non-goals.

See also: [NO-TOKEN-FIRST.md](../NO-TOKEN-FIRST.md) · [ACCOUNTABILITY-BOUNDARY.md](./ACCOUNTABILITY-BOUNDARY.md) · [ENTITY-EQUALITY.md](./ENTITY-EQUALITY.md)

---

## Native primitives (build here)

| Primitive | Meaning |
|-----------|---------|
| **Entity** | First-class contributor/witness/finalizer — any intelligent subject |
| **Contribution event** | Verifiable work unit with evidence and multi-Entity attribution |
| **Witness consensus** | Advisory multi-verifier scores; does not alone change rights |
| **Policy finalization** | Automated, traceable verdict → CP / AI Credits / reputation |
| **Ledger memory** | Append-only hash-linked record of rights-changing events |
| **Graph memory** | Collaboration relationships with Merkle-commitment |
| **Portable proof** | Exportable packet verifiable without trusting the exporter |
| **Federation opt-in** | Nodes choose which peers and policies to accept |

These are PoCP-native — not wrappers around a single vendor API or chain.

---

## Borrowed patterns (respect in code, don't sell as product)

| Source | PoCP use | External narrative |
|--------|----------|-------------------|
| Bitcoin | Hash chain, Merkle, SPV audit, issuance discipline | Contribution verification — not currency |
| MCP / A2A | Tool and agent interop | Capability receipts into Entity model |
| ERC-8004-style feedback | Agent reputation signals | Advisory; not on-chain identity |
| SourceCred | Graph weight hints | Advisory propagation only |

Mappings live under [docs/inspiration-mappings/](./inspiration-mappings/).

---

## Automation defaults

1. **Entity-equal finalization** — no human protocol gate ([ENTITY-EQUALITY.md](./ENTITY-EQUALITY.md))
2. **Witnesses advise; policy finalizes** — Clarion-0 and LLM witnesses never alone approve
3. **Traceability on rights changes** — who/which policy finalized is always recorded
4. **Instance sovereignty** — operators may opt into stricter human delegates locally

---

## Anti-patterns (reject)

| Anti-pattern | Why |
|--------------|-----|
| Token-first launch | Violates [NO-TOKEN-FIRST.md](../NO-TOKEN-FIRST.md) |
| Human-only finalization in protocol spec | Blocks Agent/LLM-native networks |
| Trust operator DB without verify | Breaks portable proof story |
| Auto-approve on tool success alone | Skips witness + policy layer |
| Permanent admin mint | Bypasses ledger + issuance budget |

---

## Engineering checklist for new features

- [ ] Does it produce or consume **evidence**?
- [ ] Does it route through **Entity** attribution?
- [ ] If it changes CP/BC/reputation, is there a **ledger row**?
- [ ] Can a third party **verify offline** (proof or audit CLI)?
- [ ] Is automation default with **optional** human delegate documented?

---

## Related

- [ARCHITECTURE-EVOLUTION.md](./ARCHITECTURE-EVOLUTION.md)
- [CORE-TECH-STACK.md](./CORE-TECH-STACK.md)
- [PROTOCOL-SPEC-v0.1.md](../PROTOCOL-SPEC-v0.1.md)
