# Model Context Protocol (MCP) → PoCP Mapping

**Status:** evaluating · **Registry slug:** `mcp`  
**Source:** [github.com/modelcontextprotocol/spec](https://github.com/modelcontextprotocol/spec) · [modelcontextprotocol.io](https://modelcontextprotocol.io/)

MCP standardizes **tool servers**, capability discovery, and **invoke** semantics. PoCP maps MCP to **Tool Entity** + **InvocationTrace** + **Capability Receipt** — protocol memory, not a generic tool runtime.

Related: [CAPABILITY-INTEGRATION.md](../CAPABILITY-INTEGRATION.md) · AgentSkills (`SKILL.md`) is a parallel Skill import path.

---

## PoCP protocol primitives touched

| Primitive | MCP concept | PoCP target |
|-----------|-------------|-------------|
| Entity (`tool`) | MCP Server + Tools | `POST /entities/tool`, `mcp_import.py` |
| Capability Receipt | tool call result | `capability_receipt.py`, step `metadata` |
| InvocationTrace | client → server → tool | `mcp_invoke.py`, `invoke_tool` action |
| Contribution Graph | tool used in task | graph edge `invoke_tool` / `invoke_mcp` |
| Evidence | call logs / artifacts | evidence items + request/response hash |

---

## Borrow (adapter layer — partial today)

| MCP spec pattern | PoCP module | Status |
|------------------|-------------|--------|
| Server manifest (name, version, capabilities) | `backend/services/mcp_import.py` | **active** (import) |
| Tool list → child Tool entities | `capabilities/import/mcp` | **active** |
| `tools/call` invoke semantics | `backend/services/mcp_invoke.py` | **active** |
| Proof packet MCP layer | `backend/services/mcp_invocation_context.py` | **active** |
| Transport (stdio / HTTP) | bundled manifests + env config | partial |
| Resource / prompt surfaces | Tool metadata JSON | evaluating |
| Peer routing across nodes | `remote_mcp_invoke.py`, `peer_mcp.py` | prototype (NN-5) |

---

## Do not borrow

| MCP pattern | Reason |
|-------------|--------|
| MCP as **the** PoCP runtime | PoCP protocol layer remembers; MCP is capability transport |
| Auto-approve contribution from tool success | Tool output ≠ verified contribution; Human finalizer required |
| Single global MCP registry | Federation: each node registers tools locally |
| Replacing Skill Entity with MCP only | Skills (SKILL.md / StudyAgent) remain first-class |
| OAuth secrets in proof packets | Instance config only; redact in export |

---

## Invocation chain (target topology)

```text
Human (initiator)
  → Agent (optional coordinator)
    → Tool Entity (MCP server)
      → Tool Entity (MCP tool child)
        → LLM (optional witness / formatter)

Each hop: InvocationStep + capability_receipt (endpoint, request_hash, response_hash)
Contribution submit: link trace_id in evidence
```

---

## Gap analysis

| Item | Current PoCP | MCP-aligned next step |
|------|--------------|------------------------|
| Tool Entity in Pilot tasks | MCP demo time server bundled | `[Pilot]` task requiring MCP Tool in participants |
| Capability receipt on MCP invoke | `mcp_invoke.py` records trace | Attach provider + duration in step `metadata` |
| MCP schema version pin | Ad hoc manifests | `metadata.mcp_spec_version` from official spec tag |
| Federation | Local invoke only | Peer MCP witness (already stubbed in intelligence API) |

---

## Integration workflow

```text
1. Pin MCP spec version in mcp_import metadata
2. Enrich mcp_invoke step metadata → capability_receipt in proof
3. Pilot task: Human + Agent + MCP Tool + LLM witness
4. Status evaluating → pattern_borrowed when Pilot path green
```

**Entity ID:** `pocp-insp-mcp` · **portable_id:** `github:modelcontextprotocol/spec`

**Official SDKs (reference only, do not fork):** [modelcontextprotocol/python-sdk](https://github.com/modelcontextprotocol/python-sdk), [modelcontextprotocol/typescript-sdk](https://github.com/modelcontextprotocol/typescript-sdk)
