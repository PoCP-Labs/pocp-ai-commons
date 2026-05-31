# External Integrations

PoCP borrows proven patterns from adjacent open-source projects **without** adopting token-first or chain-required assumptions. This document maps each integration to its inspiration and the PoCP API surface.

See also: [NO-TOKEN-FIRST.md](../NO-TOKEN-FIRST.md) · [EVIDENCE-STANDARD-v0.1.md](./EVIDENCE-STANDARD-v0.1.md)

---

## 1. OCTP — Provenance Envelope

**Inspired by:** [openoctp/spec](https://github.com/openoctp/spec) (Open Contribution Trust Protocol)

**PoCP module:** `backend/services/provenance.py`

Contributors can declare how work was created (`human_written`, `ai_assisted`, `ai_generated`, `mixed`) plus cited human experts and AI tools used. The envelope is stored under `evidence._pocp.provenance` and exported in contribution proof packets.

**Submit example:**

```json
POST /api/v1/contributions
{
  "task_id": "...",
  "primary_entity_id": "...",
  "evidence": {"url": "https://example.com/guide"},
  "provenance": {
    "creation_mode": "ai_assisted",
    "ai_tools_used": ["cursor", "claude"],
    "human_experts_cited": ["github:rain"],
    "review_depth": "self_reviewed"
  }
}
```

---

## 2. GARL / RECEIPT — Agent Action Receipts

**Inspired by:** [Garl-Protocol/garl](https://github.com/Garl-Protocol/garl), [MorkeethHQ/receipt](https://github.com/MorkeethHQ/receipt)

**PoCP module:** `backend/services/agent_receipt.py`

Each invocation trace (`Human → Agent → Skill → LLM`) can export a SHA-256 hash + optional Ed25519 node signature.

| Method | Path |
|--------|------|
| GET | `/api/v1/invocations/{trace_id}/receipt` |
| POST | `/api/v1/invocations/{trace_id}/receipt/verify` |

Configure `POCP_NODE_PRIVATE_KEY` / `POCP_NODE_PUBLIC_KEY` for signed receipts (same keys as federation proofs).

---

## 3. ERC-8004 — Off-Chain Agent Reputation

**Inspired by:** [erc-8004/erc-8004-contracts](https://github.com/erc-8004/erc-8004-contracts)

**PoCP module:** `backend/services/agent_reputation.py`, table `agent_feedback`

PoCP implements the **Reputation Registry pattern off-chain**: structured feedback with self-feedback prevention, compatible field names (`value_dec`, tags), no wallet required.

| Method | Path |
|--------|------|
| POST | `/api/v1/agents/{agent_id}/feedback` |
| GET | `/api/v1/agents/{agent_id}/reputation/summary` |
| GET | `/api/v1/agents/{agent_id}/reputation/clients` |

---

## 4. Meritocrab / GARL — External HTTP Verifiers

**Inspired by:** [hydai/meritocrab](https://github.com/hydai/meritocrab), external verifier plugins

**PoCP module:** `backend/services/verifiers/http_verifier.py`, `backend/config/verifiers.yaml`

Register additional advisory verifiers that accept PoCP context JSON and return Clarion-compatible scores. Loaded by `MultiVerifierService` via `load_verifier_providers()`.

```yaml
# backend/config/verifiers.yaml
external_verifiers:
  - name: my_lab_verifier
    enabled: true
    url: https://lab.example/api/pocp/verify
    api_key_env: POCP_VERIFIER_MY_LAB_VERIFIER_API_KEY
```

Set `ENABLE_MOCK_VERIFIER=false` to use OpenAI + DeepSeek + configured HTTP plugins in production.

---

## 5. Contributor Attribution — Impact Context

**Inspired by:** [drdeeks/contributor-attribution](https://github.com/drdeeks/contributor-attribution)

Code path hints in contribution evidence are matched against `code_attribution.yaml` and exported in proof packets.

| Method | Path |
|--------|------|
| GET | `/api/v1/contributions/{id}/code-attribution-context` |

Proof layer: `code_attribution_context`

---

## 6. proof-of-contribution — Expert Cards

**Inspired by:** [dannwaneri/proof-of-contribution](https://github.com/dannwaneri/proof-of-contribution)

Resolve `human_experts_cited` portable IDs into entity cards with reputation totals.

| Method | Path |
|--------|------|
| GET | `/api/v1/contributions/{id}/experts` |

Proof layer: `expert_cards`

---

## 7. Meritocrab — Reward Advisory & Human Reject

**Inspired by:** [hydai/meritocrab](https://github.com/hydai/meritocrab)

AI consensus `suggested_cp` / `suggested_credits` surfaced for finalizers (advisory). Explicit reject endpoint with ledger record.

| Method | Path |
|--------|------|
| GET | `/api/v1/contributions/{id}/reward-advisory` |
| POST | `/api/v1/contributions/{id}/reject` |

---

## 8. OCTP Integrity — Signed Provenance & URL Checks

Provenance envelopes are hash-signed when node keys are configured. Optional URL validation on submit (`POCP_VALIDATE_EVIDENCE_URLS=true`).

| Method | Path |
|--------|------|
| GET | `/api/v1/contributions/{id}/evidence-check` |

---

## 9. ERC-8004 — Agent Registration

**Inspired by:** [erc-8004/erc-8004-contracts](https://github.com/erc-8004/erc-8004-contracts)

Off-chain agent identity registration with capabilities and service endpoints.

| Method | Path |
|--------|------|
| POST | `/api/v1/agents` |

---

## 10. Genesis Witness Verifiers — Lumen-0 & DeSui

Genesis LLM witness nodes run as named verifier adapters in `MultiVerifierService` when `ENABLE_GENESIS_WITNESSES=true` (default).

---

## 11. Meritocrab — Reputation Audit Trail

Every reputation change from approval, federation import, or code attribution sync is recorded in `reputation_audit_entries`.

| Method | Path |
|--------|------|
| GET | `/api/v1/entities/{id}/reputation/audit` |

---

## 12. TrustMyGit — Git Commit Evidence & Portable Reputation

Validate commit SHAs via local git or GitHub API. Export portable off-chain reputation bundles.

| Method | Path |
|--------|------|
| GET | `/api/v1/contributions/{id}/evidence-check` | URL + git combined |
| GET | `/api/v1/entities/{id}/reputation/portable` |
| GET | `/api/v1/federation/reputation/{portable_id}/portable` |

---

## 13. Unified Clarion-0 Review Packet

Clarion heuristic rubric merges with AI multi-consensus, expert cards, code attribution, and evidence checks in one packet.

| Method | Path |
|--------|------|
| GET | `/api/v1/contributions/{id}/clarion-review` |

`ClarionVerifier` also participates in `MultiVerifierService`.

---

## 14. Meritocrab — Request Changes & Webhooks

Human reviewers can send contributions back for revision without full rejection. Optional webhooks fire on approve/reject/request-changes (`config/webhooks.yaml`).

| Method | Path |
|--------|------|
| POST | `/api/v1/contributions/{id}/request-changes` |

---

## 15. What We Deliberately Did Not Import

| Project | Reason |
|---------|--------|
| Agent Commons / TrustMyGit | Token-first economics conflict with [NO-TOKEN-FIRST.md](../NO-TOKEN-FIRST.md) |
| Lineage / on-chain iNFT | Chain-required royalty settlement not needed for Sprint Alpha |
| Meritocrab PR gating | PoCP uses advisory AI + human approval, not repo write gates |

---

## 16. contributor-attribution — Merkle Attribution Proof

Builder impact shares are hashed into a Merkle tree for verifiable attribution without trusting the analysis server.

| Method | Path |
|--------|------|
| GET | `/api/v1/contributions/{id}/attribution-proof` |
| POST | `/api/v1/contributions/{id}/attribution-proof/verify` |

Proof layer: `attribution_merkle_proof`

---

## 17. OCTP — Verification Claims

Provenance envelopes now accept `verification_claims` (e.g. `self_reviewed`, `ci_passed`, `peer_reviewed`).

---

## 18. Meritocrab — Finalization Queue

Contributions in `ai_verified` status may appear in a finalization queue (optional manual step when auto-finalize is off).

| Method | Path |
|--------|------|
| GET | `/api/v1/reviews/queue` |

---

## 19. Frontend Integration Surfaces

- **EntityDetail**: portable reputation, audit trail, agent feedback summary
- **ContributionInsights**: Clarion unified packet, reward advisory, Merkle root, approve/reject/request-changes actions
- **SubmitFlow**: OCTP provenance + verification claims on submit

---

## 20. External Inspiration Entity Registry

Borrowed OSS projects are recorded as **community entities** with documented contribution rows — not just documentation.

**PoCP module:** `backend/services/external_inspiration.py`, `backend/config/external_inspirations.yaml`

| Method | Path |
|--------|------|
| GET | `/api/v1/external-inspirations/report` |
| GET | `/api/v1/external-inspirations/inspirations/{slug}` |
| POST | `/api/v1/external-inspirations/sync` |

Proof layer: `external_inspirations_context`

See [EXTERNAL-INSPIRATION-REGISTRY.md](./EXTERNAL-INSPIRATION-REGISTRY.md).

**Round 5 additions:** CHAOSS transparency reports, All Contributors registries, Open Source Guides governance docs, ForgeFed-style federation — all as `community` entities with graph edges `learned_from` / `uses_pattern_from`.

| Method | Path |
|--------|------|
| GET | `/api/v1/external-inspirations/entities/{entity_id}` |
| GET | `/api/v1/contributions/{id}/external-inspirations` |

**Federation peer community entities:** `GET /api/v1/federation/peers/entities` — trusted nodes as `community` entities with graph edges `trusts_peer` / `federated_with` / `hosts`.

---

## 21. Ollama — Local LLM Witness & Embeddings (NN-2)

**Inspired by:** [ollama/ollama](https://github.com/ollama/ollama)

**PoCP modules:** `backend/services/verifiers/ollama_verifier.py`, `backend/services/ollama_client.py`, `backend/services/embedding_match.py`, `backend/services/ai_chat.py`

Local inference for advisory verification and AI chat — no cloud API key. Federation nodes can run their own witness stack.

| Capability | Env | Notes |
|------------|-----|-------|
| MultiVerifier witness | `ENABLE_OLLAMA_VERIFIER=true` | Joins consensus when mock mode is off or alongside mock in dev |
| AI chat provider | `provider=ollama` on chat endpoint | Uses `OLLAMA_MODEL` |
| Skill/agent match boost | `ENABLE_OLLAMA_EMBEDDINGS=true` | Blends keyword fit with `OLLAMA_EMBED_MODEL` (default `nomic-embed-text`) |

```bash
ollama pull llama3.2
ollama pull nomic-embed-text
ENABLE_OLLAMA_VERIFIER=true
ENABLE_OLLAMA_EMBEDDINGS=true
```

Registry: `GET /api/v1/intelligence/neural-sources` · config: `backend/config/neural_network_sources.yaml`

---

## 22. LangGraph — StudyAgent Runtime (NN-3)

**Inspired by:** [langchain-ai/langgraph](https://github.com/langchain-ai/langgraph)

**PoCP modules:** `backend/services/agent_runtimes/study_agent_runtime.py`, `backend/services/study_agent.py`

Multi-step StudyAgent flow with full **Human → Agent → Skill → LLM** `InvocationTrace`:

```http
POST /api/v1/intelligence/agents/study/run
Authorization: Bearer <token>
Content-Type: application/json

{"topic": "R matrix operations", "task_id": "<optional>", "llm_provider": "mock"}
```

| Mode | When |
|------|------|
| `state_machine_v1` | Default — no extra deps |
| `langgraph` | `pip install langgraph` + `ENABLE_LANGGRAPH_STUDY_AGENT=true` |

Output includes `draft` (advisory), `graph_steps`, and `invocation_chain` for contribution evidence.

### Submit contribution (NN-3 closed loop)

```http
POST /api/v1/intelligence/agents/study/run
{"topic": "R matrix ops", "task_id": "<task-uuid>", "submit_contribution": true}
```

Creates a **submitted** Contribution Event with `evidence.study_agent.trace_id` linked to the InvocationTrace. Then:

```http
POST /api/v1/contributions/{id}/auto-verify
```

Automated test: `python backend/scripts/study_agent_loop_test.py`

---

## 23. SourceCred — Contribution Graph Weights (evaluating)

**Inspired by:** [sourcecred/sourcecred](https://github.com/sourcecred/sourcecred)

**Mapping:** [inspiration-mappings/sourcecred.md](./inspiration-mappings/sourcecred.md)

**Borrow:** plugin-style graph ingestion, CredRank-style **advisory** propagation, instance-configurable edge weights.

**Reject:** Grain token, Cred-as-payout without Human finalizer.

**Target modules:** `graph.py`, `graph_analytics.py`, `graph_gnn_advisory.py`

Response includes `sourcecred_advisory` block (PageRank hints, advisory only).

---

## 24. Proof-of-Contribution Protocol Core — pow.yaml Interop (evaluating)

**Inspired by:** [Gitdigital-products/Proof-of-Contribution-Protocol-Core](https://github.com/Gitdigital-products/Proof-of-Contribution-Protocol-Core)

**Mapping:** [inspiration-mappings/poc-protocol-core.md](./inspiration-mappings/poc-protocol-core.md)

**Borrow:** JSON Schema for contribution metadata, CI validation patterns, DAO-composable proof records.

**Reject:** pow.yaml as sole canonical format (PoCP proof packet is strict superset).

**Target modules:** `evidence.py`, `proof.py`, `pow_export.py`

| Method | Path | Status |
|--------|------|--------|
| GET | `/api/v1/contributions/{id}/proof` | active |
| GET | `/api/v1/contributions/{id}/pow` | active — pow interop export |

---

## 25. Model Context Protocol (MCP) — Tool Entity (evaluating)

**Inspired by:** [modelcontextprotocol/spec](https://github.com/modelcontextprotocol/spec)

**Mapping:** [inspiration-mappings/mcp.md](./inspiration-mappings/mcp.md)

**Borrow:** server/tool manifests, invoke semantics, transport patterns → Tool Entity + Capability Receipt.

**Reject:** MCP as replacement for Skill Entity or auto-approve on tool success.

**Target modules:** `mcp_import.py`, `mcp_invoke.py`, `capability_receipt.py`, `remote_mcp_invoke.py`

| Method | Path | Status |
|--------|------|--------|
| POST | `/api/v1/capabilities/import/mcp` | active |
| POST | `/api/v1/capabilities/mcp/invoke` | active — returns `capability_receipts` + step `metadata` |
| POST | `/api/v1/intelligence/peer/mcp/invoke` | prototype |

---

## Router

All integration endpoints live under `backend/routers/integrations.py` with tag `integrations`.

---

## 26. Bitcoin — Verify-Don't-Trust Memory Layer

**Inspired by:** [bitcoin/bitcoin](https://github.com/bitcoin/bitcoin)

**Mapping:** [inspiration-mappings/bitcoin.md](./inspiration-mappings/bitcoin.md)

**Borrow:** append-only hash chain, Merkle commitments, SPV-style proof inclusion, independent audit nodes, issuance discipline via ledger-only mint.

**Reject:** currency, mining, PoW consensus as protocol requirement, chain-as-product narrative.

**PoCP modules:** `ledger_chain.py`, `ledger_merkle.py`, `ledger_anchor.py`, `graph_merkle.py`, `verify_standalone.py`, `wallet_audit.py`, `anchor_cosign.py`, `scripts/audit_node.py`

| Method | Path | Role |
|--------|------|------|
| GET | `/api/v1/ledger/verify` | Replay hash chain |
| GET | `/api/v1/ledger/anchor` | Merkle + graph root + cosign |
| GET | `/api/v1/graph/merkle-root` | Collaboration graph commitment |
| GET | `/api/v1/graph/merkle-proof/contribution/{id}` | Graph SPV |
| POST | `/api/v1/proof/verify` | Offline packet verify |
| GET | `/api/v1/wallets/audit` | Replay balances from transactions |
| GET | `/api/v1/crypto/readiness` | Hybrid suite / PQC readiness |

See [PORTABLE-PROOF-FEDERATION.md](./PORTABLE-PROOF-FEDERATION.md) · [QUANTUM-READINESS.md](./QUANTUM-READINESS.md).

---

## 27. Compute Adapters — Akash / Render / io.net / Gensyn (evaluating)

**Inspired by:** [Akash Network](https://akash.network/) · [Render Network](https://rendernetwork.com/) · [io.net](https://io.net/) · [Gensyn](https://www.gensyn.ai/)

**Mapping:** [COMPUTE-ADAPTER-SPEC.md](./COMPUTE-ADAPTER-SPEC.md) · [inspiration-mappings/akash.md](./inspiration-mappings/akash.md) · [inspiration-mappings/ionet.md](./inspiration-mappings/ionet.md) · [inspiration-mappings/gensyn.md](./inspiration-mappings/gensyn.md)

**Borrow:** external provider registration, contribution-bound job dispatch, `ComputeReceipt` with `external_job_id`, GPU / training resource units as evidence.

**Reject:** AKT / RNDR / IO as PoCP settlement currency; job success auto-finalizes contributions; rebuilding DePIN or training markets inside PoCP.

**PoCP modules:** `services/compute_adapters/*`, `compute_jobs.py`, `compute_receipt.py`, `compute_settlement.py`

| Method | Path | Role |
|--------|------|------|
| GET | `/api/v1/compute/adapters` | Adapter catalog |
| POST | `/api/v1/compute/adapters/{slug}/import` | Register provider Entity |
| POST | `/api/v1/compute/adapters/{slug}/jobs` | Submit external job (stub/live) |
| POST | `/api/v1/compute/adapters/{slug}/jobs/{job_id}/poll` | Poll + receipt |
| GET | `/api/v1/contributions/{id}/compute-jobs` | Jobs bound to a contribution |

Registry slugs: `akash`, `render-network`, `io-net`, `gensyn` in `external_inspirations.yaml` round 8.

Proof layers in contribution packets: `mcp_invocation_context` (MCP steps) · `compute_attribution` (receipt hashes) · training attestation under `receipt.integrity.training_attestation`.

---

## 28. Training Contribution — Gensyn pattern (evaluating)

**Inspired by:** [Gensyn](https://www.gensyn.ai/) decentralized training / verification network

**Mapping:** [TRAINING-CONTRIBUTION-SPEC.md](./TRAINING-CONTRIBUTION-SPEC.md) · [inspiration-mappings/gensyn.md](./inspiration-mappings/gensyn.md) · [protocol/CAPABILITY-SCHEMA-v0.3.md](./protocol/CAPABILITY-SCHEMA-v0.3.md)

**Borrow:** training-as-work evidence schema, external verifier slot, checkpoint / metric attestation on `ComputeReceipt`.

**Reject:** on-chain training market as PoCP spine; token settlement substituting CP / AI Credits.

**PoCP modules:** `training_contribution.py`, `contribution_submit.py`, `compute_adapters/gensyn.py`, `SubmitFlow.jsx` (training type + optional adapter dispatch)

| Method | Path | Role |
|--------|------|------|
| POST | `/api/v1/contributions` | `contribution_type: training` + `evidence.training.*` |
| POST | `/api/v1/compute/adapters/gensyn/jobs` | Contribution-bound training job (stub) |
| GET | `/api/v1/contributions/{id}/proof` | Includes compute + training settlement layers |

Schema: `backend/config/schemas/training_contribution_v0.1.yaml` · evidence standard `pocp.training_contribution.v0.1`.
