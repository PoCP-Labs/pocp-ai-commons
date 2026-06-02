# PoCP Capability Internet Protocol Patch

This is the overall architecture patch for PoCP as a large-scale protocol network.

Core positioning:

> PoCP is the decentralized contribution, invocation, settlement, and reputation protocol for AI capability and compute networks.

Chinese positioning:

> PoCP 是面向 AI 能力与算力网络的去中心化贡献证明、能力调用、价值结算与声誉协议。

## What this patch connects

```text
Protocol Layer
+ Entity Node Layer
+ Public Internet Node Layer
+ Capability Layer
+ Discovery Layer
+ Invocation Ledger
+ Proof Layer
+ Verification Layer
+ Settlement Layer
+ Reputation Graph
+ Protocol Economy
+ Event Log
```

## Main files

- `CAPABILITY-INTERNET-PROTOCOL.md`
- `POCP-NETWORK-ARCHITECTURE.md`
- `MINIMUM-LIVING-NETWORK.md`
- `POCP-TOTAL-PATCH-ROADMAP.md`
- `docs/protocol/*`
- `docs/public-node/*`
- `docs/p2p/*`
- `docs/security/*`
- `docs/implementation/*`
- `backend/services/cip/*`
- `backend/models/cip.py`

## Apply

```bash
cd pocp-ai-commons
python /path/to/pocp_capability_internet_protocol_patch/apply_capability_internet_protocol_patch.py
```

Then paste `CURSOR_APPLY_PROMPT.md` into Cursor.

## Suggested branch

```bash
git checkout -b capability-internet-protocol
git add .
git commit -m "Add Capability Internet Protocol architecture and public node skeleton"
git push origin capability-internet-protocol
```
