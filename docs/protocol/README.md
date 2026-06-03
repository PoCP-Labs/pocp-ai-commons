# PoCP Protocol — Capability-First (v0.4)

**PoCP is a verifiable market for compute and AI capabilities on the existing Internet.**  
Entities publish supply; consumers invoke by the unit; the exchange chain + ledger record every settlement.

| Document | Role |
|----------|------|
| [../CAPABILITY-FIRST-POSITIONING.md](../CAPABILITY-FIRST-POSITIONING.md) | **Product narrative** — 算力 + 能力 |
| [CHAIN-AND-NODE-PLAN-v0.1.md](./CHAIN-AND-NODE-PLAN-v0.1.md) | **Start here (engineering)** — chains + nodes |
| [EXCHANGE-SPINE-v0.1.md](./EXCHANGE-SPINE-v0.1.md) | Exchange events (`exchange_settled`) |
| [CAPABILITY-SCHEMA-v0.3.md](./CAPABILITY-SCHEMA-v0.3.md) | Capability types & units |
| [ENTITY-CONNECTION.md](./ENTITY-CONNECTION.md) | **Entity linking** — structural / protocol / operational |
| [ENTITY-DIALOGUE-PROTOCOL.md](./ENTITY-DIALOGUE-PROTOCOL.md) | **Entity dialogue** — L2 native envelope (Entity ↔ Entity / boundary) |
| [PROTOCOL-EVENT-NETWORK.md](./PROTOCOL-EVENT-NETWORK.md) | **Event overlay** — L1.5 mempool · batch · Merkle (Bitcoin-inspired) |
| [BINDING-TO-DIALOGUE.md](./BINDING-TO-DIALOGUE.md) | **Binding map** — REST/A2A → dialogue kinds |
| [TRUST-POLICY-BUNDLE.md](./TRUST-POLICY-BUNDLE.md) | **Federation import** — trust + finalization + validation |
| [INVOCATION-SCHEMA-v0.3.md](./INVOCATION-SCHEMA-v0.3.md) | InvocationTrace + step matrix |
| [CONSTITUTION-v0.1.md](./CONSTITUTION-v0.1.md) | Invariants |
| [ENTITY-NODE-MANIFEST-v0.1.md](./ENTITY-NODE-MANIFEST-v0.1.md) | Node manifest (→ v0.2 facets) |
| [THREAT-MODEL-v0.1.md](./THREAT-MODEL-v0.1.md) | Security |

**Internal / secondary:** [NEURAL-ARCHITECTURE-v0.1.md](./NEURAL-ARCHITECTURE-v0.1.md) · [LANDING-PLAN-v0.1.md](./LANDING-PLAN-v0.1.md)

**v0.3 schemas** (entity, settlement, invocation) remain valid. v0.4 adds capability-first exchange spine + provider node facets.

---

## CIP 12-layer specs (Capability Internet)

Normative layer specs for the [12-layer capability internet](../POCP-NETWORK-ARCHITECTURE.md). In-memory reference skeleton: `backend/services/cip/` · demo: `python backend/scripts/minimum_living_network.py`.

| # | Layer | Spec |
|---|-------|------|
| 1 | Entity | [ENTITY-LAYER-SPEC.md](./ENTITY-LAYER-SPEC.md) · [ENTITY-SCHEMA-v0.3.md](./ENTITY-SCHEMA-v0.3.md) |
| 2 | Node | [NODE-RUNTIME-SPEC.md](./NODE-RUNTIME-SPEC.md) · [ENTITY-NODE-MANIFEST-v0.1.md](./ENTITY-NODE-MANIFEST-v0.1.md) |
| 3 | Identity | [DID-SIGNATURE-SPEC.md](./DID-SIGNATURE-SPEC.md) · [TRUST-POLICY-BUNDLE.md](./TRUST-POLICY-BUNDLE.md) |
| 4 | Capability | [CAPABILITY-SCHEMA.md](./CAPABILITY-SCHEMA.md) · [CAPABILITY-SCHEMA-v0.3.md](./CAPABILITY-SCHEMA-v0.3.md) |
| 5 | Discovery | [CROSS-NODE-INTERNET.md](./CROSS-NODE-INTERNET.md) · [PUBLIC-NODE-PROTOCOL.md](./PUBLIC-NODE-PROTOCOL.md) |
| 6 | Invocation | [INVOCATION-LEDGER-SPEC.md](./INVOCATION-LEDGER-SPEC.md) · [INVOCATION-SCHEMA-v0.3.md](./INVOCATION-SCHEMA-v0.3.md) |
| 7 | Proof | [PROOF-SPEC.md](./PROOF-SPEC.md) |
| 8 | Verification | [VERIFICATION-NETWORK-SPEC.md](./VERIFICATION-NETWORK-SPEC.md) |
| 9 | Settlement | [SETTLEMENT-SPEC.md](./SETTLEMENT-SPEC.md) · [EXCHANGE-SPINE-v0.1.md](./EXCHANGE-SPINE-v0.1.md) |
| 10 | Reputation | [REPUTATION-GRAPH-SPEC.md](./REPUTATION-GRAPH-SPEC.md) |
| 11 | Governance | [GOVERNANCE-SPEC.md](./GOVERNANCE-SPEC.md) · [CONSTITUTION-v0.1.md](./CONSTITUTION-v0.1.md) |
| 12 | Economy | [PROTOCOL-ECONOMY-SPEC.md](./PROTOCOL-ECONOMY-SPEC.md) · [TOKEN-ACCOUNT-SPEC.md](./TOKEN-ACCOUNT-SPEC.md) |
| — | Event log | [PROTOCOL-EVENT-SPEC.md](./PROTOCOL-EVENT-SPEC.md) · [PROTOCOL-EVENT-NETWORK.md](./PROTOCOL-EVENT-NETWORK.md) |

Agent Studio mission: [capability_internet](../agents/missions/capability-internet/MANIFEST.md) · backlog: [CAPABILITY-INTERNET-BACKLOG.md](../agent-studio/CAPABILITY-INTERNET-BACKLOG.md).
