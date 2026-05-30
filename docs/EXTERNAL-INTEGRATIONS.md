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

AI consensus `suggested_cp` / `suggested_credits` surfaced for human reviewers (advisory only). Explicit human reject endpoint with ledger record.

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

## 18. Meritocrab — Human Review Queue

Contributions in `ai_verified` status appear in a review queue for human final approval.

| Method | Path |
|--------|------|
| GET | `/api/v1/reviews/queue` |

---

## 19. Frontend Integration Surfaces

- **EntityDetail**: portable reputation, audit trail, agent feedback summary
- **ContributionInsights**: Clarion unified packet, reward advisory, Merkle root, approve/reject/request-changes actions
- **SubmitFlow**: OCTP provenance + verification claims on submit

---

## Router

All integration endpoints live under `backend/routers/integrations.py` with tag `integrations`.
