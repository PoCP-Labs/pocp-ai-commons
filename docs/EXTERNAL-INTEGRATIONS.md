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

PoCP's code attribution registry (`/api/v1/code-attribution/*`) already tracks path-level builder attribution. Provenance + verifier context now carry **impact signals** (creation mode, cited experts) into AI advisory review rather than auto-pay splits.

Future bridge: embed code attribution summaries into proof packets.

---

## 6. What We Deliberately Did Not Import

| Project | Reason |
|---------|--------|
| Agent Commons / TrustMyGit | Token-first economics conflict with [NO-TOKEN-FIRST.md](../NO-TOKEN-FIRST.md) |
| Lineage / on-chain iNFT | Chain-required royalty settlement not needed for Sprint Alpha |
| Meritocrab PR gating | PoCP uses advisory AI + human approval, not repo write gates |

---

## Router

All integration endpoints live under `backend/routers/integrations.py` with tag `integrations`.
