# Cursor Prompt: Apply PoCP Capability Internet Protocol Patch

You are working in `PoCP-Labs/pocp-ai-commons`.

## Goal

Upgrade PoCP from an AI Commons application into the foundation of a distributed AI capability and compute network.

Target positioning:

```text
PoCP is the decentralized contribution, invocation, settlement, and reputation protocol for AI capability and compute networks.
```

Chinese:

```text
PoCP 是面向 AI 能力与算力网络的去中心化贡献证明、能力调用、价值结算与声誉协议。
```

## Architecture chain to enforce

```text
Entity
→ NodeProfile / PublicNode
→ DID / PublicKey
→ Capability
→ Discovery
→ Handshake
→ Invocation
→ Proof
→ Verification
→ Settlement
→ TokenAccount
→ ReputationGraph
→ ProtocolEventLog
```

## README update

Add a top-level section:

```markdown
## PoCP Capability Internet Protocol

PoCP is the decentralized contribution, invocation, settlement, and reputation protocol for AI capability and compute networks.

It treats every Human, Agent, LLM, Skill, Tool, Dataset, Workflow, Compute Node, Verifier, Reviewer, Organization, Sponsor, and Treasury as an Entity.

Each Entity can optionally run as a PoCP Node. Public Nodes may expose internet endpoints, publish capabilities, receive invocations, submit proofs, acknowledge settlements, and build reputation.

PoCP AI Commons remains the first application scenario, while PoCP Capability Internet Protocol defines the larger network architecture.
```

Add links to the new docs.

## Backend integration

The patch adds skeletons under:

```text
backend/services/cip/
```

Make them import cleanly.

Do not break the existing Genesis Demo.

If existing SQLAlchemy model style differs, keep `backend/models/cip.py` as a model proposal until adapted.

## API target

Add or plan:

```http
POST /api/v1/entities
POST /api/v1/nodes/register
POST /api/v1/nodes/{node_id}/heartbeat
GET  /api/v1/nodes/discover
POST /api/v1/capabilities
GET  /api/v1/capabilities/search
POST /api/v1/invocations
POST /api/v1/proofs
POST /api/v1/proofs/{proof_id}/verify
POST /api/v1/settlements
GET  /api/v1/token-accounts/{entity_id}
GET  /api/v1/reputation/{entity_id}
GET  /api/v1/graph/entities/{entity_id}
GET  /api/v1/events/{entity_id}
```

Public node endpoints:

```http
GET  /.well-known/pocp-node.json
GET  /pocp/node
GET  /pocp/health
GET  /pocp/capabilities
POST /pocp/handshake
POST /pocp/invoke
POST /pocp/proofs
GET  /pocp/settlements
POST /pocp/settlements/ack
GET  /pocp/sync
```

## Minimum living network demo

Preserve or create a demo that shows:

```text
Human / Agent Node
→ discovers Public Skill Node
→ handshakes
→ invokes code_review capability
→ Skill Node returns output hash
→ Skill Node submits proof
→ Verifier Node verifies proof
→ Settlement distributes CP / AIC
→ Reputation Graph updates
→ Protocol events are emitted
```

## Strict rules

- Do not present PoCP as a simple AI app.
- Do not introduce public token issuance.
- CP / AIC / CC / PT are internal accounting units only.
- Do not commit private keys or production secrets.
- Do not include private user data.
- Do not break the existing AI Commons loop.
- Public node communication must include signed requests, timestamp, nonce, and replay protection design.

## Suggested commit

```text
Add Capability Internet Protocol architecture and public node skeleton
```
