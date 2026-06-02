# Cursor Prompt: Add Bitcoin-Inspired PoCP Network Skeleton

You are working in `PoCP-Labs/pocp-ai-commons`.

## Goal

Implement a Bitcoin-inspired network skeleton for PoCP without copying Bitcoin mining or creating a public token.

Borrow the useful protocol mechanisms:

```text
P2P nodes
independent verification
event broadcast
mempool
hash chain
Merkle root
event batch
light node verification
confirmation status
incentive alignment
anti-Sybil controls
```

Map them into PoCP:

```text
Entity Node Network
Capability Discovery
Invocation Ledger
Proof Ledger
Verification Network
Settlement Event Log
Reputation Graph
ProtocolEvent Batch
Challenge / Confirmation
```

## README update

Add a section:

```markdown
## Bitcoin-Inspired PoCP Network

PoCP borrows Bitcoin's protocol design principles, not its mining model.

Bitcoin proves value transfers without a central bank.
PoCP aims to prove AI capability invocation, contribution, verification, settlement, and reputation without a central AI platform.

The mapping is:

- Bitcoin Node → PoCP Entity Node
- Bitcoin Transaction → PoCP Invocation / Proof / Settlement Event
- Bitcoin Mempool → PoCP Pending Invocation / Proof / Settlement Pools
- Bitcoin Block → PoCP EventBatch
- Merkle Root → PoCP EventBatch root
- SPV Light Node → PoCP Light Node
- Miner → PoCP Verifier / Indexer / Settlement Node
- Block Explorer → PoCP Reputation Graph Explorer
```

## Backend integration

The patch adds skeletons under:

```text
backend/services/network/
```

Make sure they import cleanly.

Run:

```bash
python backend/scripts/bitcoin_inspired_network_smoke.py
```

## Do not

- Do not introduce PoW mining.
- Do not introduce public token issuance.
- Do not break the existing Genesis Loop.
- Do not replace the Capability Internet Protocol docs.
- Do not commit private keys, secrets, user data, or unreleased exploit details.
