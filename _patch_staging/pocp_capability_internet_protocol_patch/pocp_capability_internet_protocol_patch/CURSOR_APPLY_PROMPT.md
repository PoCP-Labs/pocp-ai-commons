# Cursor Prompt: Upgrade PoCP AI Commons into Capability Internet Protocol Core

You are working in `PoCP-Labs/pocp-ai-commons`.

## Goal

Keep `PoCP AI Commons` as the first reference application, but upgrade the repository toward:

```text
Entity → NodeProfile → PublicNodeEndpoint → Capability → Invocation → Proof → Verification → Settlement → TokenAccount → ReputationGraph → ProtocolEvent
```

## README update

Add near the top of `README.md`:

```markdown
## PoCP Capability Internet Protocol

PoCP AI Commons is the first reference application of the PoCP Capability Internet Protocol.

PoCP aims to become a decentralized contribution, invocation, settlement, and reputation protocol for AI capability and compute networks.

AI Commons starts with the first living loop:

Contribution → Verification → CP → AI Credits → AI Use → More Contribution

The larger PoCP network expands this into:

Entity → NodeProfile → PublicNodeEndpoint → Capability → Invocation → Proof → Verification → Settlement → TokenAccount → ReputationGraph → ProtocolEvent

See:
- [Capability Internet Protocol](CAPABILITY-INTERNET-PROTOCOL.md)
- [PoCP Network Architecture](POCP-NETWORK-ARCHITECTURE.md)
- [Minimum Living Network](MINIMUM-LIVING-NETWORK.md)
- [Migration from AI Commons](MIGRATION-FROM-AI-COMMONS.md)
- [Public Skill Node Closed Loop](PUBLIC-SKILL-NODE-CLOSED-LOOP.md)
- [Protocol Roadmap PR Sequence](PROTOCOL-ROADMAP-PR-SEQUENCE.md)
```

## Immediate engineering tasks

1. Fix backend formatting first if Python files are compressed into one long line.
2. Preserve the current Genesis Loop.
3. Integrate the added service skeletons carefully.
4. Run:

```bash
python backend/scripts/capability_internet_smoke.py
```

## Target API set

```http
POST /api/v1/entities
POST /api/v1/nodes/register
POST /api/v1/nodes/{node_id}/heartbeat
GET  /api/v1/nodes/discover
POST /api/v1/capabilities
GET  /api/v1/capabilities
POST /api/v1/invocations
POST /api/v1/proofs
POST /api/v1/proofs/{proof_id}/verify
POST /api/v1/settlements
GET  /api/v1/token-accounts/{entity_id}
GET  /api/v1/reputation/{entity_id}
GET  /api/v1/graph/entities/{entity_id}
GET  /api/v1/protocol-events
```

## Do not

- Do not break the existing contribution → verify → approve → ledger demo.
- Do not introduce public token issuance.
- Do not commit private keys, API keys, production secrets, user private data, or unreleased exploit details.

## Suggested PR title

```text
Add Capability Internet Protocol core architecture
```
