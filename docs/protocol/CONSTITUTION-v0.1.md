# PoCP Constitution v0.1

**Status:** normative for v0.4 neural base  
**Scope:** All PoCP instances claiming `protocol: pocp-v0.4-neural-base`

These rules are the PoCP equivalent of Bitcoin consensus rules. Code, operators, and federation peers **must not** violate them silently.

---

## Preamble

PoCP records **verifiable exchange of compute and intelligence** and **rights that follow contribution**.  
**Entity** is the network subject (neuron). **Operator servers** are optional hosts for Archive roles — not the definition of a node.

---

## Article I — Memory (不可篡改记忆)

1. **Append-only ledger.** `ledger_records` are never updated or deleted in place; corrections append compensating rows.
2. **Hash linkage.** Every ledger row after genesis carries `prev_hash` → `record_hash` under declared `hash_algorithm`.
3. **Dual commitment.** Periodic anchors commit **at minimum** `ledger_merkle_root` and `graph_merkle_root`.
4. **Balance truth.** For any wallet, `cp_balance` and `ai_credits` **must equal** the sum of `credit_transactions` (replay audit).
5. **Issuance path.** Positive BC/CP mint **only** via `credit_transactions` created inside `issue_right()` or documented settlement paths, subject to `issuance_budget`.

---

## Article II — Exchange (算力/智力交换通路)

6. **Exchange settlement row.** Any BC debit/credit caused by capability invoke, compute job, or AI chat **must** emit a ledger event mappable to `exchange_settled` (see [EXCHANGE-SPINE-v0.1.md](./EXCHANGE-SPINE-v0.1.md)).
7. **Receipt binding.** Every `exchange_settled` references a `receipt_hash` and/or `invocation_trace_id` recoverable offline.
8. **Quote before spend.** Consumer-facing spend APIs **should** expose quote (`/wallets/me/quote`) matching actual burn amount.

---

## Article III — Neurons (Entity 节点)

9. **Entity identity.** Network participation is attributed to `entity_id`; anonymous burns without entity attribution are forbidden in production paths.
10. **Witness attribution.** Verifier output stored for finalization **must** record `witness_entity_id` (LLM/Agent Entity), not only provider string.
11. **Node manifest.** Active Entities offering capabilities or witness **must** publish a node manifest (API or `/.well-known/pocp-node.json`).
12. **No self-finalization without policy.** An Entity **must not** finalize its own contribution unless explicit policy allows and audit flags it.

---

## Article IV — Activation (贡献终局)

13. **Policy finalization.** Transition to `approved` requires traceable finalization: `finalizer_entity_id`, `policy_id`, `policy_version`.
14. **Witness quorum.** Auto-finalize requires configured minimum distinct witness Entities (instance policy).
15. **Graph inclusion.** Approved contributions **must** appear in contribution graph with participant edges before or atomically with finalize.

---

## Article V — Federation (联邦互认)

16. **Graduated import.** Cross-node import **must** declare acceptance level L0–L3 (see [LANDING-PLAN-v0.1.md](./LANDING-PLAN-v0.1.md)); default L1.
17. **No silent rights mint on mirror.** Read-only mirror nodes **must not** create local BC/CP without import proof.
18. **Crypto suite floor.** Imported proofs below `POCP_MIN_CRYPTO_SUITE` are rejected.

---

## Article VI — Verification (验证优先)

19. **Portable proof.** Every approved contribution **must** export a proof packet verifiable offline.
20. **Independent audit.** Instances **should** expose `/ledger/verify`, `/wallets/audit`, and support `audit_node.py remote`.

---

## Enforcement

| Mechanism | Owner |
|-----------|--------|
| CI constitution tests | `backend/tests/test_constitution.py` (planned) |
| Smoke + federation acceptance | `scripts/smoke_test.py`, `run_phase_a_acceptance.py` |
| Code review checklist | PR template references this file |

Violations are **protocol bugs**, not operator discretion.
