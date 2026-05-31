# Agent Marketplace Benchmarks → PoCP Mapping

**Status:** evaluating · **Registry slugs:** `singularitynet`, `fetch-ai`  
**Declined related:** `bittensor`, `virtuals-protocol` (token markets)

---

## Shared lesson

SingularityNET, Fetch.ai, and similar stacks solve **AI service / agent discovery and payment**. PoCP solves **contribution proof after invocation**.

```text
Marketplace  =  list + buy AI service
PoCP         =  record multi-entity chain + verify + settle + graph
```

---

## Borrow

| Pattern | PoCP target |
|---------|-------------|
| Service / agent catalog | A2A Agent Card + capability import |
| Agent task delegation | `a2a_task_bridge.py` → Contribution + InvocationTrace |
| Agent reputation | ERC-8004 off-chain pattern (already borrowed) |

---

## Reject

| Pattern | Reason |
|---------|--------|
| AGIX / FET / subnet token as PoCP currency | NO-TOKEN-FIRST |
| Agent coin issuance (Virtuals) | ENTITY-MARKET-SPEC rejected models |
| Marketplace order book as source of truth | Ledger + Proof Packet |

---

## Complement stack

Use **A2A + MCP** for orchestration; PoCP Entity remains accountability anchor for Humans and sponsored Agents.
