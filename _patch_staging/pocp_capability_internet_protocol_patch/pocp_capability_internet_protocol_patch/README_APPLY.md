# PoCP Capability Internet Protocol Patch

This patch upgrades `pocp-ai-commons` from a first AI Commons application into the protocol core for:

> PoCP Capability Internet Protocol — a decentralized contribution, invocation, settlement, and reputation protocol for AI capability and compute networks.

It keeps **PoCP AI Commons** as the first reference application, while adding the larger protocol architecture:

```text
Entity
→ NodeProfile
→ PublicNodeEndpoint
→ Capability
→ Invocation
→ Proof
→ Verification
→ Settlement
→ TokenAccount
→ ReputationGraph
→ ProtocolEvent
```

## Apply

```bash
cd pocp-ai-commons
python /path/to/pocp_capability_internet_protocol_patch/apply_capability_internet_protocol_patch.py
```

Then paste `CURSOR_APPLY_PROMPT.md` into Cursor.

## Suggested branch

```bash
git checkout -b capability-internet-protocol-core
git add .
git commit -m "Add Capability Internet Protocol core architecture"
git push origin capability-internet-protocol-core
```

## Important

This patch does not introduce public token issuance. `CP`, `AIC`, `CC`, and `PT_INTERNAL` are protocol accounting units unless future governance, legal, and security review explicitly changes that.
