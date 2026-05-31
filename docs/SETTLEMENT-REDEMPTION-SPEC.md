# Settlement & Redemption Spec v0.4 (draft)

**What can be redeemed, cashed out, or on-ramped — and what must stay protocol-internal until governance and legal maturity.**

See also: [NO-TOKEN-FIRST.md](../NO-TOKEN-FIRST.md) · [ENTITY-MARKET-SPEC.md](./ENTITY-MARKET-SPEC.md) · [COMPUTE-METERING-SPEC.md](./COMPUTE-METERING-SPEC.md) · [COMPUTE-BALANCE-SPEC.md](./COMPUTE-BALANCE-SPEC.md) · [AI-CREDITS-CP-REPUTATION.md](../AI-CREDITS-CP-REPUTATION.md) · [NEURAL-INTERNET-MASTER-PLAN.md](./NEURAL-INTERNET-MASTER-PLAN.md) · [genesis/zh-CN.md](./genesis/zh-CN.md) §10

---

## 1. Scope

This spec answers:

> Can PoCP Token, CP, or ComputePool balance be **redeemed** for fiat, Bitcoin, or other external value?

It separates three layers that are often conflated:

| Layer | Question | This spec |
|-------|----------|-----------|
| **Settlement** | Who pays whom inside PoCP after verified work? | Covered by [ENTITY-MARKET-SPEC.md](./ENTITY-MARKET-SPEC.md) §6 |
| **Metering** | How much PoCP Token moves per Receipt? | [COMPUTE-METERING-SPEC.md](./COMPUTE-METERING-SPEC.md) |
| **Redemption** | Can internal balances exit to external money? | **This document** |

**Redemption** means converting protocol-internal rights into **external, transferable financial value** (fiat, stablecoin, BTC, etc.) through an approved exit path.

PoCP **settlement** (Entity-to-Entity earn/spend) is not redemption.

---

## 2. Terminology

| Term | Meaning | Redeemable? |
|------|---------|-------------|
| **PoCP Token** | Wallet field `ai_credits`; unified metering + settlement unit | See §3–4 |
| **AI Credits** | Legacy name for PoCP Token in API/docs | Same as PoCP Token |
| **CP** | Contribution Points — verified contribution value | **Never** |
| **Reputation** | Contextual trust record | **Never** |
| **ComputePool** | Org-level PoCP Token reservoir for burst/precompute | **Internal only** (Pilot) |
| **Sponsor pool / deposit** | Org-granted PoCP Token for members or tasks | **Internal grant**, not fiat on-ramp |
| **Org treasury** | Off-protocol fiat budget for external cloud adapters | **Buys compute**, not PoCP Token mint |

```text
Contribution → CP (proof) + PoCP Token (spend) + Reputation (trust)
                     ↓
              Entity market settlement (earn/spend)
                     ↓
              Optional external exit (redemption) — governance-gated only
```

---

## 3. Pilot — what can and cannot be redeemed

### 3.1 Official Pilot position

```text
PoCP Pilot has NO tradable protocol coin.
PoCP Token is an internal usage right (ai_credits).
CP and Reputation are non-financial records.

There is NO protocol-level redemption to fiat or crypto in Pilot.
```

This aligns with [NO-TOKEN-FIRST.md](../NO-TOKEN-FIRST.md) and [genesis/zh-CN.md](./genesis/zh-CN.md) §11: *第一阶段不发行代币；没有分红承诺.*

### 3.2 What contributors **can** do (Pilot)

| Action | Mechanism | Redemption? |
|--------|-----------|-------------|
| Earn PoCP Token | Verified contribution → wallet credit | No — usage right |
| Spend PoCP Token | AI Chat, Skill, compute jobs, witness | No — burns for service |
| Earn as provider | ComputeReceipt / IntelReceipt settlement | No — reinvest in network |
| Receive sponsor grant | Org `POST /compute/pools/{org}/deposit` | No — internal pool transfer |
| Export Proof | Proof Packet with ledger + receipts | No — audit, not cash-out |

### 3.3 What is **explicitly out of scope** (Pilot)

| Forbidden in Pilot | Why |
|--------------------|-----|
| PoCP Token → fiat off-ramp | Would imply securities / e-money without legal frame |
| PoCP Token OTC / P2P transfer | Violates non-transferable Pilot wallet model |
| CP → money or Token swap | CP is not spendable ([AI-CREDITS-CP-REPUTATION.md](../AI-CREDITS-CP-REPUTATION.md)) |
| Protocol-operated exchange | Token-first architecture |
| “Withdraw balance” UI | Misleading; no withdrawal path exists |
| Promised yield on PoCP Token | NO-TOKEN-FIRST anti-pattern |

### 3.4 Fiat in Pilot (on-ramp only, off-protocol)

Fiat **may** enter a deployment, but **not** as a PoCP Token minting on-ramp for individuals:

```text
Org / Sponsor ── fiat (off-protocol) ──► Org treasury
                              │
                              ├──► external cloud adapter (OpenAI, etc.) — Step 5 escalation
                              └──► sponsor budget → internal PoCP Token pool deposit (org policy)
```

| Path | Role | PoCP protocol involvement |
|------|------|---------------------------|
| Treasury → cloud API | Buys **compute capacity** when mesh insufficient | Receipt notes `source: external`; no Token mint from fiat |
| Sponsor → pool deposit | Distributes **pre-allocated** internal credits | Ledger `compute_pool_*`; org-governed |
| User pays org in fiat | **Off-protocol** membership / tuition / CSR | Org decides internal grant; not protocol on-ramp |

See [COMPUTE-BALANCE-SPEC.md](./COMPUTE-BALANCE-SPEC.md) §4.2, §7.

**Key invariant:** Fiat funds **external compute purchase** or **org-sponsored grants** — it does not create a redeemable PoCP Token float.

---

## 4. v1.0 — optional redemption paths (governance-gated)

Redemption is **not** a launch feature. It becomes discussable only after [NO-TOKEN-FIRST.md](../NO-TOKEN-FIRST.md) maturity conditions (real networks, bilateral usage, anti-abuse, ledger, reputation, governance need, value pool, **legal analysis**).

### 4.1 What v1.0 **might** allow (if approved)

| Path | Description | Preconditions |
|------|-------------|---------------|
| **Treasury redemption (limited)** | Org redeems **provider-earned** PoCP Token against org treasury for **documented compute subsidy** | Governance vote; jurisdiction review; caps |
| **Protocol Token (optional)** | Tradable on-chain unit **after** contribution network maturity | Separate spec; not Pilot |
| **Provider settlement export** | Federation reconciliation of cross-node balances | Settlement, not individual cash-out ([ENTITY-MARKET-SPEC.md](./ENTITY-MARKET-SPEC.md) §9) |

### 4.2 What v1.0 still rejects by default

| Rejected unless explicit governance + legal | Reason |
|---------------------------------------------|--------|
| Retail fiat off-ramp for any Entity | E-money / MSB exposure |
| CP redemption | CP is proof, not currency |
| Anonymous redemption | Sybil + laundering risk |
| Protocol custody of user fiat/crypto | Centralization + regulatory surface |

### 4.3 Governance checklist (before any redemption module)

1. Jurisdiction map (org domicile, user residence, provider locations)  
2. Licensed partner or org-only treasury path  
3. Redemption caps, KYC tier, audit trail linked to Receipt + Ledger  
4. Public disclosure: no guaranteed value, no investment promise  
5. Network vote or multi-org charter amendment  
6. Rollback plan if abuse detected  

---

## 5. Fiat on-ramp / off-ramp governance

### 5.1 Roles

| Role | On-ramp (fiat → capability) | Off-ramp (capability → fiat) |
|------|----------------------------|------------------------------|
| **Organization treasury** | Pays cloud adapters; funds sponsor pools | Pilot: **none**. v1.0: optional org-only provider settlement |
| **Sponsor** | Deposits internal credits from contribution/CSR budget | **Never** individual cash-out in Pilot |
| **Protocol treasury** | Reserved; fee sink only if configured | **Not** a user withdrawal desk |
| **Individual Entity** | **No** direct protocol on-ramp in Pilot | **No** off-ramp in Pilot |

### 5.2 On-ramp principles (Pilot + v1.0)

```text
1. Fiat enters OFF-PROTOCOL at Org boundary.
2. Protocol records INTERNAL grants and EXTERNAL adapter calls — not wire transfers.
3. Every subsidized job still produces Receipt → Proof → Ledger.
4. Sponsor deposits require authorized sponsor Entity + audit reason.
```

**Compliance hooks (implementation-facing):**

| Control | Pilot | v1.0+ |
|---------|-------|-------|
| Sponsor deposit authorization | `sponsor` role + org scope | + approval workflow |
| External adapter flag | `source: external` on Receipt | + treasury reference id |
| Pool balance alerts | `pool_low_sponsor_deposit` | + policy caps |
| Proof export | Full attribution for funders | + impact report for sponsors |

### 5.3 Off-ramp principles (v1.0+ only)

If ever enabled:

```text
1. Off-ramp is ORG- or GOVERNANCE-scoped — not a global “Withdraw” button.
2. Redemption tied to verified provider service (Receipt-backed), not idle balance speculation.
3. Rate limits, minimum service period, and reputation gates apply.
4. PoCP protocol does not hold user bank accounts; licensed partner or org treasury executes payout.
```

---

## 6. Bitcoin / crypto optional path

Bitcoin and other crypto assets are **not required** for PoCP balance or settlement ([COMPUTE-BALANCE-SPEC.md](./COMPUTE-BALANCE-SPEC.md) §7).

### 6.1 Non-custodial principles

If a deployment optionally accepts BTC or stablecoin:

| Principle | Requirement |
|-----------|-------------|
| **Non-custodial default** | Protocol does not hold private keys for user wallets |
| **Adapter pattern** | Entity-level or Org-level payment adapter — same as external cloud adapter |
| **No protocol hot wallet** | Avoid pooled custody; reduces hack + regulatory surface |
| **Receipt anchoring** | On-chain tx hash may appear in Receipt `extra`; settlement still PoCP Token internally |
| **Optional** | Nodes MAY disable crypto entirely; federation must not require it |

```text
User / Org ── BTC (self-custody wallet) ──► Org adapter (optional)
                        │
                        └──► org policy → internal grant OR external service payment
                                    │
                                    └── NOT automatic PoCP Token mint without org rule + ledger entry
```

### 6.2 BTC as redemption asset (future)

| Model | PoCP position |
|-------|---------------|
| User sells PoCP Token for BTC on DEX | **Out of scope** unless Protocol Token + legal framework |
| Provider paid in BTC by Org treasury | **Off-protocol** employment / contractor settlement |
| Lightning micro-pay per Receipt | Research only; Receipt-first accounting still required |

**Anti-pattern:** Marketing “earn Bitcoin on PoCP” before contribution loop and compliance exist.

---

## 7. Relationship to PoCP Token, CP, and ComputePool

### 7.1 PoCP Token

- **Pilot:** Single internal unit (`ai_credits`); metering = settlement ([COMPUTE-METERING-SPEC.md](./COMPUTE-METERING-SPEC.md) §2).  
- **Earn:** Contribution grants + provider settlement.  
- **Spend:** Consumer jobs, pool burst, federation reconciliation.  
- **Redemption:** **None** in Pilot; v1.0 treasury path **optional** and governance-gated (§4).

### 7.2 CP

- Records **how much** was contributed — not a wallet spend unit.  
- **Never redeemable** for fiat, crypto, or PoCP Token via protocol swap.  
- Any future “CP influence” is governance/reputation — not cash exit.

### 7.3 ComputePool

- Org-level **reservoir** of PoCP Token for surplus/deficit balancing ([COMPUTE-BALANCE-SPEC.md](./COMPUTE-BALANCE-SPEC.md) §5).  
- **Not** a redemption vault or escrow for fiat.  
- Pool `deposit` = internal credit allocation; `spend` = burst/precompute — not withdrawable to bank.

```text
┌─────────────────────────────────────────────────────────┐
│ Wallet (PoCP Token)  ←── settlement ←── Receipt         │
│ CP (non-spend)       ←── contribution finalize          │
│ Reputation           ←── long-term reliability          │
│ ComputePool          ←── org buffer (internal only)     │
└─────────────────────────────────────────────────────────┘
         │ Pilot: no exit arrow to fiat/BTC
         ▼
   v1.0: optional governance-gated treasury redemption (dashed)
```

---

## 8. Anti-patterns

| Anti-pattern | Why it violates NO-TOKEN-FIRST | Correct framing |
|--------------|----------------------------------|-----------------|
| “Invest in PoCP Token” | Implies security / return | Contribute → earn **usage rights** |
| Withdraw UI for `ai_credits` | Implies deposit liability | Insufficient balance → contribute or sponsor grant |
| Fiat on-ramp mints Token 1:1 for retail | E-money without license | Org treasury → adapter or sponsor pool only |
| CP → Token exchange | Makes CP a shadow currency | Separate records; CP stays non-spendable |
| Anonymous cross-Entity transfers | OTC market by another name | Bilateral settlement with Receipt + context |
| BTC custody in protocol DB | Centralized honeypot | Non-custodial adapter at Org boundary |
| Redemption before bilateral market proof | Narrative without network | Complete [ENTITY-MARKET-SPEC.md](./ENTITY-MARKET-SPEC.md) Pilot criteria first |
| “Price of PoCP Token” marketing | Speculation-first | Metering rates in yaml — not market cap |

---

## 9. Phase matrix

| Phase | PoCP Token | Redemption | Fiat | BTC/crypto |
|-------|------------|------------|------|------------|
| **Pilot (now)** | Internal `ai_credits`; non-transferable | **None** | Org treasury → external adapter only | Not supported |
| **v0.4** | Federation bilateral settlement; pool cron | **None** | Same as Pilot | Not supported |
| **v0.5** | Dynamic pricing; SLA | **None** | Same | Research adapters |
| **v1.0** | Optional Protocol Token (governance vote) | Optional treasury redemption (governance + legal) | Licensed / org-scoped on-ramp | Optional non-custodial Org adapter |

---

## 10. Implementation notes (v0.4)

No redemption API ships in v0.4. Relevant **existing** surfaces:

| Surface | Redemption relevance |
|---------|---------------------|
| `POST /compute/pools/{org}/deposit` | Internal sponsor grant — document as non-redemption |
| `compute_settlement.py` | Bilateral Token flow — not off-ramp |
| Receipt `source: external` | Marks fiat-backed cloud job — not Token mint |
| Proof export | Audit for sponsors — not withdrawal proof |
| `pocp_rewards.yaml` | Metering rates — not exchange rates |

**Do not add** `/wallet/withdraw`, `/redeem`, or `/on-ramp` in Pilot without governance spec amendment.

---

## 11. External positioning

> PoCP Token is a **contribution-bound usage right** inside the network — not a tradable coin in Pilot.  
> Organizations may use **off-protocol fiat** to fund cloud compute or sponsor internal credit pools.  
> **Redemption to fiat or Bitcoin is not offered** until the contribution network, bilateral market, and legal framework mature — and only through **governance-approved, org-scoped** paths.

Chinese genesis alignment: [genesis/zh-CN.md](./genesis/zh-CN.md) §10.4 — PoCP Token 是协议内使用权，不是可场外炒作的协议币.

---

## 12. One line

> **Settle inside with Receipt; sponsor with Org treasury; redeem only after governance says so — and never confuse usage rights with money.**
