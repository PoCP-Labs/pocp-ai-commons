# Entity Market Spec v0.2 (draft)

**Contribution-attributed bilateral market for distributed compute and intelligence — not a centralized GPU cloud selling tokens.**

See also: [COMPUTE-METERING-SPEC.md](./COMPUTE-METERING-SPEC.md) · [SETTLEMENT-REDEMPTION-SPEC.md](./SETTLEMENT-REDEMPTION-SPEC.md) · [DISTRIBUTED-TOKEN-RESEARCH.md](./DISTRIBUTED-TOKEN-RESEARCH.md) · [DISTRIBUTED-COMPUTE-PRIMER.md](./DISTRIBUTED-COMPUTE-PRIMER.md) · [DISTRIBUTED-INTELLIGENCE.md](./DISTRIBUTED-INTELLIGENCE.md) · [NO-TOKEN-FIRST.md](../NO-TOKEN-FIRST.md) · [AI-CREDITS-CP-REPUTATION.md](../AI-CREDITS-CP-REPUTATION.md)

---

## 1. Thesis

Centralized AI platforms sell access from a single operator:

```text
User ── fiat / platform credits ──► Big platform GPU API
                      │
                      └── only the platform issues and captures margin
```

PoCP enables a **distributed Entity market**:

```text
Entity A (LLM provider)  ── sells compute  ──► earns settlement Token
Entity B (Skill provider)  ── sells intelligence ──► earns settlement Token
Entity C (Human / Org)     ── consumes both ──► spends settlement Token
         ▲                                              │
         └──── contribution → verification → initial Token ──┘
              Receipt + InvocationTrace + Ledger prove every trade
```

**Innovation claim (must be provable in Pilot):**

> Any verified Entity can **sell** compute and intelligence and **earn** settlement Token; any Entity can **buy** with Token — without PoCP operating a centralized GPU farm or being the sole token issuer.

This is distinct from:

| Model | PoCP position |
|-------|---------------|
| OpenAI / cloud API | Rejected as **architecture center** — PoCP routes to Entity providers |
| Bittensor-style token mining | Rejected — NO-TOKEN-FIRST; anonymous miner markets |
| Web2 points | Rejected — no portable Proof or Contribution Graph |
| **PoCP Entity market** | **Accepted direction** — bilateral, contribution-bound, receipt-audited |

---

## 2. Economic loop

```text
┌──────────────────────────────────────────────────────────────┐
│ 1. INFLOW — Contribution verified → CP + AI Credits + Rep  │
└────────────────────────────┬─────────────────────────────────┘
                             ▼
┌──────────────────────────────────────────────────────────────┐
│ 2. CONSUME — Entity spends Token on compute / intelligence │
└────────────────────────────┬─────────────────────────────────┘
                             ▼
┌──────────────────────────────────────────────────────────────┐
│ 3. PROVIDE — Provider Entities earn Token per Receipt      │
└────────────────────────────┬─────────────────────────────────┘
                             ▼
┌──────────────────────────────────────────────────────────────┐
│ 4. REINVEST — Earned Token funds more contribution & jobs    │
└────────────────────────────┬─────────────────────────────────┘
                             ▼
┌──────────────────────────────────────────────────────────────┐
│ 5. MEMORY — Ledger + Contribution Graph grow together        │
└──────────────────────────────────────────────────────────────┘
```

When this loop closes with real jobs (not mock-only), PoCP’s economy is **operationally** distinct from centralized token sellers.

---

## 3. Participants

| Role | Entity types | Sells | Buys |
|------|--------------|-------|------|
| **Compute provider** | LLM, Tool, Org node | `llm_inference`, `embeddings`, `witness` execution | — |
| **Intelligence provider** | Skill, Agent, LLM (witness) | matching, orchestration, verification | compute from others |
| **Consumer** | Human, Agent, Org | — | compute + intelligence |
| **Sponsor** | Organization, Community | Token grants (bounties) | impact / governance |

Every participant is an **Entity** with a **Wallet** (`cp_balance`, `ai_credits`).

---

## 4. Listing compute & intelligence (seller side)

### 4.1 ComputeProfile (shipped v0.1)

Entity metadata declares what it sells:

```json
{
  "compute_profile": {
    "status": "active",
    "offers": [
      {
        "capability": "llm_inference",
        "adapters": ["ollama"],
        "models": ["qwen2.5:7b"]
      }
    ],
    "endpoints": { "base_url": "http://127.0.0.1:11434" },
    "policy": { "visibility": "org_only", "accepts_public_jobs": false }
  }
}
```

### 4.2 Pricing overlay (v0.3)

Optional seller overrides within protocol caps:

```json
{
  "market_profile": {
    "spec_version": "0.2",
    "pricing_mode": "protocol_default",
    "overrides": {
      "llm_inference:qwen2.5:7b": {
        "provider_per_1k_total": 0.35
      }
    }
  }
}
```

Scheduler ranks providers by: policy match → reputation → price → latency.

---

## 5. Buying compute & intelligence (consumer side)

### 5.1 Job initiation

Jobs must bind context (anti-Sybil):

```text
required: initiator_entity_id
required one of: contribution_id | task_id
optional: org scope, federation trust
```

### 5.2 Execution path

```text
Consumer requests Skill / Chat / Verify
  → Intelligence layer routes (match, orchestrate)
  → Compute scheduler selects provider Entity
  → Executor runs on provider endpoint
  → ComputeReceipt (+ IntelReceipt) created
  → Metering ([COMPUTE-METERING-SPEC.md](./COMPUTE-METERING-SPEC.md))
  → Settlement (this spec §6)
```

### 5.3 InvocationTrace

Multi-step purchases appear as a chain:

```text
Human → Agent → Skill → LLM provider → Witness provider
```

Each billable step produces a receipt; settlement may split across providers.

---

## 6. Settlement (bilateral Token flow)

**Settlement Token (Pilot): AI Credits** — non-transferable off-protocol.

| Event | Wallet effect |
|-------|---------------|
| Contribution approved | Consumer +provider earns CP & credits (existing) |
| Job completed | Consumer `−= consumer_credits` |
| Receipt verified | Provider `+= provider_credits` |
| Intel step completed | Intel provider `+= intel_credits` |

All mutations go through `CreditTransaction` + `append_ledger_record`.

### 6.1 Idempotency

Key: `receipt_hash` (and `intel_receipt_hash`). Duplicate settlement returns `already_settled`.

### 6.2 Insufficient balance

Consumer job fails before execution with clear error (same as AI Chat today).

---

## 7. Relationship to NO-TOKEN-FIRST

| Phase | Settlement unit | Transferable | Issuer |
|-------|-----------------|--------------|--------|
| **Pilot (now)** | AI Credits | No | Protocol grants from contribution |
| **v0.2–v0.3** | AI Credits | No | Bilateral earn/spend between Entities |
| **Future (governance)** | Protocol Token | Maybe, if legal + maturity | Network rules, not launch-day ICO |

Conditions before a tradable protocol token ([NO-TOKEN-FIRST.md](../NO-TOKEN-FIRST.md)):

1. Real contribution networks  
2. Real AI Credits usage **including Entity-to-Entity trades**  
3. Anti-abuse mechanisms  
4. Reliable ledger  
5. Reputation system  
6. Governance need  
7. Value pool  
8. Legal analysis  

**Entity market with AI Credits completes step 2** without violating “no token-first.”

Redemption (fiat/BTC exit) is **out of scope for Pilot** — see [SETTLEMENT-REDEMPTION-SPEC.md](./SETTLEMENT-REDEMPTION-SPEC.md).

---

## 8. vs centralized platform (comparison table)

| Dimension | Centralized platform | PoCP Entity market |
|-----------|---------------------|-------------------|
| Seller | One operator | Many Entity providers |
| Token issuer | Platform only | Earned via service + contribution |
| Pricing | Platform table | Protocol default + Entity override |
| Audit | Opaque invoice | Receipt → Proof Packet |
| Contribution link | None | Required context on jobs |
| Federation | N/A | Cross-node provider mirror |
| Speculation | Often token-first | Contribution-first |

---

## 9. Federation & cross-node trades (v0.3+)

When consumer and provider sit on different PoCP nodes:

1. Consumer node schedules job → remote execution on provider node.  
2. Provider node issues signed ComputeReceipt.  
3. Consumer node debits local wallet; federation settlement reconciles credits (see [COMPUTE-FEDERATION-SPEC.md](./COMPUTE-FEDERATION-SPEC.md)).  
4. Proof import verifies receipt hash before honoring provider credit on consumer ledger.

---

## 10. Pilot validation criteria

The thesis is **proven** when a public demo shows:

| # | Criterion |
|---|-----------|
| 1 | ≥2 distinct provider Entities complete real `llm_inference` jobs |
| 2 | Consumer Entity balance decreases; provider balance increases |
| 3 | Amounts follow metering spec (token or documented equivalent) |
| 4 | Proof export includes `compute_attribution` with receipts |
| 5 | At least one intelligence step (witness or skill) earns separate provider credit |
| 6 | No PoCP-operated centralized GPU required |

---

## 11. Risks & guardrails

| Risk | Guardrail |
|------|-----------|
| Speculation before network | AI Credits only in Pilot; no OTC |
| Fake providers | Org vouching, reputation gate, mesh visibility |
| Wash volume | Require contribution/task binding for provider pay |
| Platform re-centralization | Default route to Entity providers, not PoCP-hosted LLM |
| Pricing race to bottom | Reputation weight in scheduler; minimum rates in yaml |

---

## 12. Implementation phases

| Phase | Deliverable |
|-------|-------------|
| **α–δ** (done) | ComputeProfile, scheduler, receipt, fixed settlement |
| **v0.2** | Token metering spec implemented; dynamic burn/credit |
| **v0.3** | IntelReceipt, split settlement, optional Entity price overrides |
| **v0.4** | Skill orchestration multi-party split (LLM + Skill + protocol fee); federation bilateral settlement |
| **v1.0** | Governance vote on protocol token (optional) |

---

## 13. Official positioning (external)

> PoCP is not a centralized compute center that sells tokens.  
> It is a **contribution-attributed market** where verified Entities sell compute and intelligence, earn settlement Token, and consumers spend Token on the network — with every trade recorded in Receipt, Proof, and Ledger.

Chinese genesis: [genesis/zh-CN.md](./genesis/zh-CN.md) §10.4.

---

## 14. One line

> **Sell compute and intelligence as an Entity; buy with Token; prove with Receipt.**
