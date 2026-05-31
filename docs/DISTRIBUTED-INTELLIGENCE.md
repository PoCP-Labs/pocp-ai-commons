# Distributed Intelligence Layer

**PoCP’s orchestration plane — witness quorum, matching, agents, graph analytics, and Entity-attached compute routing.**

See also: [DISTRIBUTED-LAYERS.md](./DISTRIBUTED-LAYERS.md) · [DISTRIBUTED-INTELLIGENCE-BUILD-GUIDE.md](./DISTRIBUTED-INTELLIGENCE-BUILD-GUIDE.md) · [CONTRIBUTION-NEURAL-NETWORK.md](./CONTRIBUTION-NEURAL-NETWORK.md) · [INTELLIGENCE-LAYER.md](./INTELLIGENCE-LAYER.md) · [DISTRIBUTED-COMPUTE-RESEARCH.md](./DISTRIBUTED-COMPUTE-RESEARCH.md) · [DISTRIBUTED-INTELLIGENCE-BENCHMARK.md](./DISTRIBUTED-INTELLIGENCE-BENCHMARK.md)

---

## Definition

The **Distributed Intelligence Layer** sits between the **Protocol Layer** (portable proof + ledger) and the **Distributed Compute Layer** (inference adapters).

It does **not** run GPUs. It:

1. Orchestrates **multi-Entity collaboration chains** (Human → Agent → Skill → LLM → Tool)
2. Aggregates **multi-witness advisory** consensus
3. **Matches** capabilities to tasks
4. Builds **advisory** graph analytics and governance summaries
5. **Routes** compute jobs to Entity providers, local node, or federation peers
6. Emits **Intelligence Packets** and **ComputeReceipts** for proof export

> AI witnesses. Policy finalizes. Ledger remembers.

---

## Architecture

```text
Protocol Layer          Entity · Contribution · Proof · InvocationTrace
        ▲
Distributed Intelligence   kernel.py + engines.py + intelligence router
        ▲
Distributed Compute        Ollama · vLLM · peer witness · MCP host
```

Code:

```text
backend/intelligence/          — CapabilityLayer kernel
backend/services/
  compute_profile.py           — Entity ComputeProfile v0.1
  compute_scheduler.py         — Provider selection pipeline
  compute_receipt.py           — Auditable compute attribution
  compute_jobs.py              — Job store (DB-backed, ComputeJobRecord)
  graph_analytics.py           — PageRank / review hints
  peer_compute.py              — NN-5 peer overlay
backend/routers/
  intelligence.py              — /api/v1/intelligence/*
  compute.py                     — /api/v1/compute/*
```

---

## Entity service matrix

| Entity | Roles | Intelligence services |
|--------|-------|---------------------|
| Human | creator, reviewer | precheck, Clarion, profile, job initiator |
| Agent | executor | matching, StudyAgent runtime, schedule |
| Skill | skill_provider | semantic matching, execute routing |
| LLM | witness, verifier | multi-verifier, peer witness, compute register |
| Tool | tool_provider | MCP invoke, compute_profile mcp_host |
| Dataset | data_provider | dedup, evidence binding |
| Workflow | coordinator | topology templates |
| Organization | sponsor | governance, compute policy |
| Community | witness, federation | peer entities, federation intel |

---

## New primitives (P1 — shipped)

### ComputeProfile (Entity metadata)

```yaml
compute_profile:
  spec_version: "0.1"
  offers:
    - capability: witness
      adapters: [ollama, mock]
  endpoints:
    base_url: "https://lab.example:8100"
  status: active
```

Register:

```http
POST /api/v1/intelligence/entities/{entity_id}/compute/register
POST /api/v1/compute/entities/{entity_id}/register
```

### ComputeJob + Scheduler

```http
POST /api/v1/compute/jobs
{
  "capability": "witness",
  "contribution_id": "...",
  "constraints": { "model": "qwen2.5:7b" }
}
```

Routing pipeline:

```text
1. local node (if adapters active)
2. Entity providers (owner-first ranking)
3. federation peer nodes (witness / inference / mcp)
→ ComputeReceipt in job record
```

### ComputeReceipt

Included in job response; future: embed in InvocationTrace → Proof Packet.

```json
{
  "spec_version": "pocp.compute_receipt.v0.1",
  "provider_entity_id": "...",
  "provider_node_id": "...",
  "capability": "witness",
  "integrity": { "receipt_hash": "..." }
}
```

---

## API surface

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/v1/intelligence/protocol/stack` | Three-layer map |
| GET | `/api/v1/intelligence/status` | Module registry |
| POST | `/api/v1/intelligence/match` | Agent/Skill matching |
| GET | `/api/v1/intelligence/graph/analytics` | Graph advisory |
| POST | `/api/v1/intelligence/entities/{id}/compute/register` | ComputeProfile |
| GET | `/api/v1/compute/providers` | Discover providers |
| POST | `/api/v1/compute/jobs` | Schedule job |
| GET | `/api/v1/compute/jobs/{id}` | Job + receipt |
| POST | `/api/v1/compute/entities/{id}/heartbeat` | Provider liveness |

---

## Feasibility

| Area | Maturity | Notes |
|------|----------|-------|
| Protocol + proof spine | ~80% | Federation, ledger, traces |
| Distributed intelligence orchestration | ~75% | Kernel + 9 modules + scheduler P1 |
| Entity compute mesh | ~50% | Profile + scheduler shipped; execution wiring next |
| Provider economics | ~20% | Credits burn on consumer only |

**Verdict:** Feasible and differentiated. PoCP competes on **verifiable attribution**, not raw FLOPS.

---

## Roadmap

### P1 ✅ (this release)

- [x] ComputeProfile validation + Entity registration
- [x] compute_scheduler v0.1
- [x] ComputeReceipt + job API
- [x] Entity profile includes compute_profile

### P2 ✅ (this release)

- [x] Wire scheduler into `capability_execute` (llm_inference + ComputeReceipt on trace step)
- [x] Wire witness scheduling into `auto-verify` consensus (`compute_schedule`)
- [x] Witness diversity policy (`min_distinct_witness_nodes` in finalization rules)
- [x] ComputeReceipt in proof packet (`invocation_trace.compute_receipts`)
- [x] Frontend Capability panel — compute provider register + job test
- [x] `POST /api/v1/compute/jobs/{id}/execute` for witness execution

### P3 (Pilot infrastructure) ✅

- [x] ComputeJob DB persistence (`models/compute_job.py`, migration `g9h0i1j2k3l4`)
- [x] Pilot witness quorum via env (`POCP_PILOT_MODE`, `POCP_MIN_DISTINCT_WITNESS_NODES`)
- [x] Peer `llm_inference` routing (`POST /api/v1/intelligence/compute/inference`)
- [x] Provider settlement (`compute_settlement` — bilateral credits on receipt)
- [x] A2A Agent Card discovery (BI-1) — `/.well-known/agent.json`, per-Entity `/agent-card`
- [x] A2A JSON-RPC task bridge (BI-1.5) — `SendMessage` → `ContributionEvent`
- [x] Peer trust handshake (BI-2) — HMAC/Ed25519 headers + `/compute/peer/challenge`

### P3 (Pilot product — open)

- [ ] Provider reputation + sponsor pool credits
- [ ] Cross-node embedding federation
- [ ] Open provider discovery (trusted mesh first)

---

## Operator quick start

```bash
# 1. Dev login → register lab LLM entity as witness provider
curl -X POST http://localhost:8000/api/v1/intelligence/entities/{llm_id}/compute/register \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "offers": [{"capability": "witness", "adapters": ["ollama"]}],
    "endpoints": {"base_url": "http://localhost:8000"},
    "status": "active"
  }'

# 2. Discover providers
curl http://localhost:8000/api/v1/compute/providers?capability=witness

# 3. Schedule advisory job
curl -X POST http://localhost:8000/api/v1/compute/jobs \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"capability": "witness", "constraints": {"input_preview": "task context"}}'

# Pilot: multi-node witness quorum (env override)
export POCP_PILOT_MODE=true
export POCP_MIN_DISTINCT_WITNESS_NODES=2
export POCP_ALLOW_PEER_WITNESS=true   # peer witness + inference
export POCP_PEER_COMPUTE_SECRET=dev-shared-secret
# BI-2: GET /api/v1/intelligence/compute/peer/trust · /compute/peer/challenge

# 4. A2A Agent Card discovery (BI-1)
curl http://localhost:8000/.well-known/agent.json
curl http://localhost:8000/api/v1/intelligence/entities/{entity_id}/agent-card

# 5. A2A SendMessage → Contribution (BI-1.5)
curl -X POST http://localhost:8000/api/v1/intelligence/entities/{agent_id}/a2a \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"SendMessage","params":{"message":{"parts":[{"kind":"text","text":"Evidence-backed change."}]},"metadata":{"taskId":"{task_id}"}}}'
```

---

## Guiding rule

When adding intelligence features, ask:

```text
Does this strengthen verifiable connection between entities,
or add opaque complexity?
```

If it strengthens **who contributed, who computed, who verified** — ship it.
