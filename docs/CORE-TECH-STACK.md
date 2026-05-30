# PoCP Core Technology Stack

PoCP's core technology is not a collage of existing tools.

It is a set of native protocol primitives that turn human-AI collaboration into portable, verifiable contribution proof.

See also: [NATIVE-TECHNOLOGY-PRINCIPLES.md](./NATIVE-TECHNOLOGY-PRINCIPLES.md) and [CONTRIBUTION-PROOF-PACKET-v0.1.md](./CONTRIBUTION-PROOF-PACKET-v0.1.md).

## Native Primitives

| Native primitive | What PoCP defines | Current implementation |
|---|---|---|
| Entity | First-class intelligent participant: human, Agent, Skill, LLM, tool, dataset, workflow, organization, community | `models/entity.py`, `models/agent.py`, `models/skill.py`, `models/organization.py` |
| Contribution Event | Atomic unit of value creation and verification | `models/contribution.py`, `routers/api.py` |
| Contribution Participant | Role, weight, and evidence attribution across multiple entities | `models/contribution.py` |
| Evidence Hash | Content-addressed proof material for contribution claims | `services/evidence.py` |
| Human-AI Verification State | AI advisory review with human final approval | `services/verifiers/*`, `services/clarion.py`, `routers/verification.py` |
| Contribution Proof Packet | Portable proof object combining event, entities, evidence, verification, graph, rights, and ledger | `services/proof.py`, `routers/export.py` |
| Contribution Graph | Native relationship graph among humans, Agents, Skills, tools, reviews, and rights | `services/graph.py`, `models/invocation.py` |
| Contribution-to-Rights Conversion | Rules that convert verified contribution into CP, AI Credits, and reputation | `services/contribution.py`, `models/wallet.py` |
| Ledger Memory | Tamper-evident record of protocol events | `models/ledger.py`, `services/ledger_chain.py` |

Frameworks host these primitives. They do not define them.

## Native Protocol Object

The native object of PoCP is the **Contribution Event**.

The portable object is the **Contribution Proof Packet**.

Endpoint:

```text
GET /api/v1/contributions/{contribution_id}/proof
```

The proof packet includes:

- contribution event;
- entity identity snapshots;
- participant roles and weights;
- evidence hash and evidence items;
- AI advisory verification results;
- human review records;
- graph edges and invocation traces;
- CP / AI Credits transactions;
- reputation state;
- ledger record hashes;
- proof hash.

## Why This Matters

The PC Internet had webpages.

The Mobile Internet had app/service interactions.

PoCP has contribution proof packets:

```text
Entity + Contribution + Evidence + Verification + Graph + Rights + Ledger
```

This is the technical basis for the Contribution Internet.

The important point is not that PoCP uses a database, an API, a graph view, or LLM calls. The important point is that PoCP defines a new contribution-native proof object and the protocol semantics around it.

## Current Public Protocol APIs

```text
GET  /api/v1/entities
GET  /api/v1/contributions
GET  /api/v1/graph
GET  /api/v1/ledger/export
GET  /api/v1/ledger/verify
GET  /api/v1/entities/{entity_id}/portable
GET  /api/v1/contributions/{contribution_id}/proof
GET  /api/v1/federation/node
```

## First Technical Moat

PoCP is not mainly a model wrapper.

Its moat is the combination of:

1. Contribution Proof Protocol.
2. Human-AI Verification Engine.
3. Contribution Graph and Reputation Engine.
4. Tamper-evident Ledger.
5. Portable proof and federation-ready APIs.

These pieces make contribution relationships visible, verifiable, and reusable across communities.

## Non-Goal

PoCP must not become a technical assembly of:

```text
LLM API + points + task board + graph UI + ledger table
```

That would be an application bundle, not a protocol.

The protocol work is to make contribution itself a native, portable, verifiable object.
