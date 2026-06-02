# PoCP Bitcoin-Inspired Network Patch

This patch turns the discussion about learning from Bitcoin's P2P network into a concrete PoCP network design package.

It does **not** copy Bitcoin mining or create a public token.

It borrows useful protocol ideas:

```text
P2P node network
independent verification
event broadcast
hash chain
Merkle root
mempool
light node
event batch
confirmation
incentive alignment
anti-Sybil / anti-spam
```

and maps them into PoCP:

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

## Apply

```bash
cd pocp-ai-commons
python /path/to/pocp_bitcoin_inspired_network_patch/apply_bitcoin_inspired_network_patch.py
```

Then paste `CURSOR_APPLY_PROMPT.md` into Cursor.

## Suggested branch

```bash
git checkout -b bitcoin-inspired-pocp-network
git add .
git commit -m "Add Bitcoin-inspired PoCP network skeleton"
git push origin bitcoin-inspired-pocp-network
```

## Important

This patch is about network design, event propagation, event batching, Merkle roots, and confirmation.

It does not introduce public token issuance.
