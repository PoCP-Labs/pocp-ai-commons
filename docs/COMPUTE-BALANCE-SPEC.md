# Compute Supply–Demand Balance Spec v0.3 (draft)

**How PoCP balances surplus and deficit distributed compute — without storing raw FLOPS.**

See also: [DISTRIBUTED-TOKEN-RESEARCH.md](./DISTRIBUTED-TOKEN-RESEARCH.md) · [COMPUTE-CAPACITY-SPEC.md](./COMPUTE-CAPACITY-SPEC.md) · [ENTITY-MARKET-SPEC.md](./ENTITY-MARKET-SPEC.md) · [COMPUTE-METERING-SPEC.md](./COMPUTE-METERING-SPEC.md)

---

## 1. User question (canonical)

> When aggregated distributed compute is **surplus**, how do we **store** it?  
> When compute is **insufficient**, how do we **actively purchase** compute?  
> Only then is the system **dynamically balanced**.

**Answer:** PoCP does not store GPU cycles. It stores **four convertible forms** on surplus, and runs **four purchase escalations** on deficit. Settlement Token (AI Credits) is the **balancing currency** between both sides.

---

## 2. Core model — compute grid with a reservoir

```text
                    ┌─────────────────────────────┐
                    │   COMPUTE RESERVOIR         │
                    │   (not FLOPS — rights &     │
                    │    artifacts & credits)     │
                    └──────────────▲──────────────┘
                                   │
     SURPLUS (supply > demand)      │      DEFICIT (demand > supply)
     ───────────────────────       │      ─────────────────────────
     · earn Credits                 │      · spend Credits
     · book capacity                │      · buy peer / federation
     · precompute artifacts         │      · external adapter (paid)
     · lower price signals          │      · sponsor pool release
     · org pool deposit             │      · queue + priority bid
```

**Dynamic balance** = reservoir inflows match outflows over time, measured in **Ledger + scheduler metrics**, not in stored watt-hours.

---

## 3. Surplus — what we «store» when compute is abundant

When the network has **idle providers** (GPU unused, witness capacity free):

| Storage form | What is stored | PoCP mechanism | Status |
|--------------|------------------|----------------|--------|
| **A. Settlement balance** | Value earned from providing compute | Provider Wallet +AI Credits on Receipt | ✅ v0.2 |
| **B. Capacity rights** | Right to use a provider slot later | `CapacityReservation` | ✅ v0.2 prototype |
| **C. Compute artifacts** | Outputs of past compute (embeddings, cached LLM answers) | `ComputeArtifact` + `cache_hit` | ✅ v0.2 prototype |
| **D. Org compute pool** | Pooled Credits + reserved slots for the org | `ComputePool` (v0.3) | 📋 spec |
| **E. Precompute jobs** | Batch work during off-peak | Scheduler `precompute` job type | 📋 v0.3 |

### 3.1 Surplus actions (automatic + policy)

```text
Idle provider detected (heartbeat active, low queue)
  → 1. Scheduler lowers effective price (within yaml floor)
  → 2. Org pool may auto-book cheap reservation windows
  → 3. Precompute: embeddings for Contribution Graph / dedup
  → 4. Artifacts stored with content hash for future cache_hit
  → 5. Provider Credits accumulate in Wallet (economic storage)
```

**Key insight:** Surplus compute is **converted into assets**, not frozen FLOPS:

```text
Surplus GPU time  →  Artifacts + Pool deposits + Wallet Credits
                     (reusable)   (future rights)  (purchasing power)
```

---

## 4. Deficit — how we «actively purchase» compute

When local / org mesh **cannot satisfy** a job:

### 4.1 Purchase escalation ladder

```text
Step 0  ComputeArtifact cache_hit          (cheapest — no GPU)
Step 1  local_node                         (free marginal if owned)
Step 2  org Entity providers               (spend Credits → provider)
Step 3  federation peer nodes              (cross-node settlement)
Step 4  public_vouched providers           (reputation gate)
Step 5  external adapter (OpenAI / cloud)  (fiat-backed — org treasury)
Step 6  queue + fail with clear error      (insufficient pool + no provider)
```

Current code: Steps 1–4 partially in `compute_scheduler.py` (local → entity → peer).  
v0.3 adds: pool-funded Step 5, priority queue Step 6.

### 4.2 Active purchase = spend Credits

Every paid step debits **consumer Wallet** (or **Org Compute Pool**) and credits **provider**:

```text
Deficit job arrives
  → scheduler finds no free local slot
  → escalates to remote Entity (higher price tier)
  → consumer Credits -= dynamic_price
  → provider Credits += settlement
  → Receipt + Ledger record purchase
```

If network Credits are insufficient:

```text
  → Org sponsor pool releases grant (bounty)
  → OR external adapter billed to org treasury (off-protocol fiat)
  → OR job queued until pool replenished
```

---

## 5. ComputePool — org-level reservoir (v0.3)

Bridges surplus and deficit inside an Organization Entity.

```json
{
  "compute_pool": {
    "spec_version": "0.3",
    "organization_entity_id": "uuid",
    "balance_credits": 5000,
    "reserved_capacity_slots": 12,
    "artifact_count": 340,
    "policy": {
      "surplus_deposit_pct": 0.20,
      "deficit_burst_limit": 500,
      "allow_external_adapter": true,
      "external_daily_cap_usd": 100
    }
  }
}
```

| Event | Pool effect |
|-------|-------------|
| Member provides compute (surplus) | Optional % of earned Credits → pool |
| Off-peak precompute | Pool pays providers; artifacts ↑ |
| Peak deficit | Pool pays escalated remote jobs |
| External API call | Pool/treasury fiat → cloud; Receipt notes `source: external` |

**This is the closest PoCP gets to « storing collective compute »** — a **shared reservoir of purchasing power + artifacts + reservations**, not stored FLOPS.

---

## 6. Dynamic balance signals

Scheduler and governance need **observable metrics**:

| Metric | Meaning | Action when high/low |
|--------|---------|----------------------|
| `provider_utilization` | jobs / capacity | High → escalate purchase; Low → precompute |
| `pool_balance_credits` | org reservoir | Low → alert sponsor; High → book reservations |
| `artifact_hit_rate` | cache_hit / total | Low → invest precompute |
| `external_adapter_ratio` | Step 5 jobs / total | High → recruit more Entity providers |
| `avg_wait_ms` | queue latency | High → raise priority pricing |

```text
Balance loop (continuous):

  measure utilization
    → surplus: store as A/B/C/D
    → deficit: purchase via escalation + pool
    → ledger reconciles Credits in = Credits out
```

---

## 7. Relationship to fiat / Bitcoin

| Layer | Role in balance |
|-------|-----------------|
| **AI Credits** | Primary balancing currency inside PoCP |
| **ComputePool** | Org-level buffer |
| **Fiat / stablecoin** | Funds **external adapter** Step 5 only (treasury) |
| **Bitcoin** | Not required for balance; optional future redemption (see redemption research) |

**Fiat enters when internal mesh is insufficient** — it buys **cloud compute**, not « stored distributed FLOPS ». Receipt still records the job for Proof.

---

## 8. Example day (Rain lab)

```text
02:00  Surplus — lab GPUs idle
       → precompute embeddings for dataset Entity
       → artifacts stored; pool -50 Credits, providers +50

09:00  Normal — students run Skill jobs
       → local Ollama + cache_hit; balanced

18:00  Deficit — peak, local queue full
       → escalate to org peer vLLM (Credits)
       → still insufficient
       → pool releases 200 Credits; federated provider accepts

22:00  Rebalance — pool balance low
       → sponsor Org deposits Credits (from contribution budget)
       → OR treasury pays OpenAI adapter for burst (fiat, Step 5)
```

---

## 9. Implementation roadmap

| Phase | Deliverable | Status |
|-------|-------------|--------|
| **v0.2** ✅ | Token metering, artifact cache, capacity reservation API | Shipped |
| **v0.3** ✅ | `ComputePool` + surplus deposit / precompute recycle | Shipped — see below |
| **v0.3** | Scheduler escalation metrics + external adapter policy flag | Partial |
| **v0.4** | Pool auto-precompute cron; federation pool settlement | Planned |
| **v1.0** | Governance-tuned balance parameters; optional treasury redemption | Planned |

### v0.3 code map (shipped)

| Component | Path |
|-----------|------|
| Utilization + idle detection | `backend/services/compute_utilization.py` |
| Org compute pool | `backend/services/compute_pool.py` |
| Surplus precompute | `backend/services/compute_precompute.py` |
| Auto pool deposit on settlement | `backend/services/compute_settlement.py` |
| API | `GET /compute/balance/summary`, `POST /compute/surplus/recycle`, `POST /compute/pools/{org}/deposit` |
| Config | `pocp_rewards.yaml` → `compute_surplus` |

**Operator flow when compute is wasted:**

```bash
# 1. Check balance / idle providers
GET /api/v1/compute/balance/summary

# 2. Sponsor fills pool (optional)
POST /api/v1/compute/pools/{org_id}/deposit  {"amount": 200}

# 3. Recycle idle GPU → artifacts
POST /api/v1/compute/surplus/recycle  {"organization_entity_id": "..."}
```

---

## 10. Anti-patterns

| Wrong | Right |
|-------|-------|
| Store « 1M FLOPS » in wallet | Store Credits + artifacts + reservations |
| Infinite external API without pool cap | `external_daily_cap` + ledger audit |
| Surplus GPU with no artifact/precompute | Waste; precompute during idle |
| Purchase without Receipt | Always Receipt → Proof |

---

## 11. One line

> **Surplus → store as Credits, capacity, and artifacts; deficit → spend Credits and escalate purchase — the grid stays balanced without a FLOPS warehouse.**
