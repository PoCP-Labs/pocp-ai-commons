# Compute & Intelligence Metering Spec v0.2 (draft)

**Unified Token metering for distributed compute and intelligence — settlement remains AI Credits until governance approves a protocol token.**

See also: [ENTITY-MARKET-SPEC.md](./ENTITY-MARKET-SPEC.md) · [DISTRIBUTED-TOKEN-RESEARCH.md](./DISTRIBUTED-TOKEN-RESEARCH.md) · [COMPUTE-FEDERATION-SPEC.md](./COMPUTE-FEDERATION-SPEC.md) · [DISTRIBUTED-COMPUTE-PRIMER.md](./DISTRIBUTED-COMPUTE-PRIMER.md) · [NO-TOKEN-FIRST.md](../NO-TOKEN-FIRST.md) · [AI-CREDITS-GUIDE.md](./AI-CREDITS-GUIDE.md)

---

## 1. Goal

PoCP must meter **real usage** of compute and intelligence services so that:

1. Consumers pay proportionally to what they use.
2. Provider Entities earn proportionally to what they supply.
3. Every charge is anchored to a **ComputeReceipt** (or **IntelReceipt**) in Proof.
4. Settlement uses **AI Credits** in Pilot; the same formulas apply if a protocol token is introduced later.

This spec defines **how much** was used (metering Token). [ENTITY-MARKET-SPEC.md](./ENTITY-MARKET-SPEC.md) defines **who pays whom** (bilateral Entity market).

---

## 2. Unified PoCP Token (metering = settlement)

**One token, one wallet field.** LLM usage counts are recorded on the receipt; **PoCP Tokens** are debited/credited from `Wallet.ai_credits` (1:1).

| Field | Meaning |
|-------|---------|
| `usage.prompt_tokens` / `completion_tokens` | Raw LLM usage from adapter (audit) |
| `pocp_tokens_consumer` / `pocp_tokens_provider` | Wallet debit/credit (same unit) |
| `token_unit` | Always `pocp_token` when `unified_token: true` |

```text
LLM tokens (receipt.usage)
        ↓  rate table (per 1k tokens → PoCP Token)
PoCP Token (Wallet.ai_credits)
        ↓
Ledger + Proof
```

Config: `compute_metering.unified_token: true` in `pocp_rewards.yaml`.

Legacy name **AI Credits** = **PoCP Token** in docs and API (`credits_*` fields kept for compatibility).

---

## 3. Metering modes

| Mode | When | Consumer charge | Provider credit |
|------|------|-----------------|-------------------|
| `receipt` | v0.1 compat, witness-only, tests | Fixed per job | Fixed per receipt |
| `token` | v0.2 default for `llm_inference` | `f(prompt, completion, model)` | `g(prompt, completion, model)` |
| `intel` | v0.2 for intelligence services | `h(intel_units, service)` | Same split rules |

Config root: `compute_metering` in `backend/config/pocp_rewards.yaml`.

---

## 4. ComputeReceipt.usage (v0.2)

Extend [ComputeReceipt](../backend/services/compute_receipt.py) with a standard `usage` block inside `extra` (v0.2) or top-level (v0.3):

```json
{
  "usage": {
    "metering_mode": "token",
    "prompt_tokens": 842,
    "completion_tokens": 156,
    "total_tokens": 998,
    "intel_equivalent_tokens": 0,
    "estimated": false,
    "estimator": null
  }
}
```

| Field | Required | Notes |
|-------|----------|-------|
| `metering_mode` | yes | `token` \| `receipt` \| `intel` |
| `prompt_tokens` | if `token` | From adapter or estimator |
| `completion_tokens` | if `token` | From adapter or estimator |
| `total_tokens` | yes | Sum or adapter total |
| `intel_equivalent_tokens` | optional | Added for blended jobs |
| `estimated` | yes | `true` if not from adapter |
| `estimator` | if estimated | `tiktoken` \| `chars/4` \| `fixed_cap` |

**Integrity:** v0.2 keeps `receipt_hash` over core execution fields; v0.3 may include `usage` in hash material once adapters are stable.

---

## 5. Adapter requirements

### 5.1 OpenAI-compatible (`/v1/chat/completions`)

Read `response.usage`:

```json
{ "prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30 }
```

### 5.2 Ollama

Ollama may omit usage. Fallback:

1. `estimated: true`, `estimator: "chars/4"` on prompt + completion text.
2. Cap per job: `max_estimated_tokens` from config (anti-abuse).

### 5.3 Mock / local

Same fallback as Ollama; flag `estimated: true` in all Pilot proofs.

### 5.4 Witness (`capability: witness`)

Default `metering_mode: receipt` or fixed `intel_equivalent_tokens` per invocation (see §6).

---

## 6. Intelligence layer metering

Intelligence services do not always invoke an LLM. Price them with **Intel equivalent tokens** or fixed settlement credits:

| Service | Receipt type | Default metering |
|---------|--------------|------------------|
| `witness` | ComputeReceipt | `receipt` or 500–2000 intel equivalent |
| `multi_verifier` quorum | ComputeReceipt × N | Sum of witness equivalents |
| `matching` | IntelReceipt (v0.2) | Fixed per recommendation |
| `skill_orchestration` | InvocationTrace step | % of downstream LLM tokens or fixed fee |
| `graph_advisory` | IntelReceipt | Fixed per query |

**IntelReceipt** (v0.2 sketch):

```json
{
  "spec_version": "pocp.intel_receipt.v0.2",
  "provider_entity_id": "uuid",
  "service": "matching",
  "intel_units": 1,
  "intel_equivalent_tokens": 1000,
  "contribution_id": "uuid",
  "task_id": "uuid"
}
```

Intel receipts merge into Proof `compute_attribution` or a sibling `intel_attribution` layer.

---

## 7. Pricing formulas

All amounts are **settlement Token** (AI Credits).

### 7.1 Consumer burn (LLM)

```text
consumer_credits = base_consumer
  + (prompt_tokens / 1000) × rate_prompt[model]
  + (completion_tokens / 1000) × rate_completion[model]
```

Round to 4 decimal places; minimum charge `min_consumer_credits` (default 0.1).

### 7.2 Provider credit (LLM)

```text
provider_credits = base_provider
  + (total_tokens / 1000) × rate_provider_total[model]
```

Idempotent by `receipt_hash` (unchanged from v0.1).

### 7.3 Intel services

```text
provider_credits = intel_units × rate_intel[service]
consumer_credits = intel_units × consumer_rate_intel[service]
```

### 7.4 Split jobs (Skill → Agent → LLM → Witness)

One consumer debit; multiple provider credits from one InvocationTrace:

```text
Human wallet  −= total_consumer_credits
Skill Entity  += orchestration_share
LLM Entity    += compute_share
Witness Entity+= witness_share
```

Shares must sum to ≤ total_consumer_credits; remainder burns (protocol fee) or returns to sponsor pool (config).

---

## 8. Configuration (`pocp_rewards.yaml`)

```yaml
compute_metering:
  mode: token                    # token | receipt
  fallback_estimator: chars/4    # tiktoken | chars/4
  max_estimated_tokens: 32000
  min_consumer_credits: 0.1
  models:
    default:
      consumer_per_1k_prompt: 0.5
      consumer_per_1k_completion: 1.0
      provider_per_1k_total: 0.3
      base_consumer: 0.0
      base_provider: 0.0
    gpt-4o-mini:
      consumer_per_1k_prompt: 0.8
      consumer_per_1k_completion: 1.5
      provider_per_1k_total: 0.5
  intel:
    witness:
      metering_mode: receipt
      provider_credits: 3.0
      consumer_credits: 5.0
    matching:
      provider_credits: 1.0
      consumer_credits: 2.0
  split:
    skill_orchestration_pct: 0.10   # of total consumer charge
    protocol_fee_pct: 0.05
```

Env overrides: `POCP_COMPUTE_METERING_MODE`, `POCP_MAX_ESTIMATED_TOKENS`.

---

## 9. Code touchpoints (implementation checklist)

| Component | Change |
|-----------|--------|
| `compute_executor.py` | Parse adapter `usage`; estimate fallback |
| `compute_receipt.py` | Standard `usage` block |
| `compute_settlement.py` | `credits_for_usage(receipt)` |
| `capability_execute.py` | Consumer burn from usage, not fixed `SKILL_EXECUTE_COST` |
| `ai_chat.py` | Same metering for chat path |
| `models/ai_usage.py` | Optional `prompt_tokens`, `completion_tokens` columns |
| `proof.py` | Export usage summary in `compute_attribution` |
| `services/intel_receipt.py` | New (v0.2) for matching/advisory |

---

## 10. Anti-abuse

| Risk | Guard |
|------|-------|
| Inflated self-reported tokens | Prefer adapter usage; cap `estimated` jobs |
| Estimated farming | Lower provider rate when `estimated: true` |
| Wash trading | Jobs require `contribution_id` or `task_id` for provider credit |
| Daily drain | Keep `DAILY_AI_CREDITS_BURN_LIMIT`; add per-entity provider daily cap |

---

## 11. Proof & ledger events

| Event | Payload |
|-------|---------|
| `ai_credits_burned` | `usage`, `consumer_credits`, `receipt_hash` |
| `compute_provided` | `usage`, `provider_credits`, `receipt_hash` |
| `intel_provided` | `intel_units`, `provider_credits` |

---

## 12. Version roadmap

| Version | Scope |
|---------|-------|
| **v0.1** (shipped) | Fixed credits per receipt / chat message |
| **v0.2** (this spec) | Token metering + dynamic settlement; AI Credits |
| **v0.3** | Entity-listed prices; `usage` in receipt hash; IntelReceipt |
| **v1.0** | Federation settlement; optional protocol token (governance + legal) |

---

## 13. One line

> **One PoCP Token: meter LLM usage, settle in Wallet, prove in Receipt.**
