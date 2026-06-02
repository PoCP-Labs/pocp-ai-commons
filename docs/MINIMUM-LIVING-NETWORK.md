# Minimum Living Network

The smallest PoCP deployment that proves **network semantics** (not just a single-server app).

Parent: [CAPABILITY-INTERNET-PROTOCOL.md](./CAPABILITY-INTERNET-PROTOCOL.md)

---

## Three nodes

| Node | Entity types | Role |
|------|--------------|------|
| **A** | Human + Agent | Task creator, orchestrator |
| **B** | Skill (public) | Publishes `code_review` capability |
| **C** | Verifier + Reviewer | AI witness + human governance proxy |

Phase A reference: Rain + StudyAgent (A), R-Tutor Skill (B), Lumen/DeSui + Bob (C) — see demo seed in `backend/seed.py`.

---

## One capability

Minimum capability type for first cross-node loop:

```text
code_review  (or study-notes / summarize in current demo)
```

Schema: [CAPABILITY-SCHEMA-v0.3.md](./protocol/CAPABILITY-SCHEMA-v0.3.md).

---

## Closed loop (13 steps)

```text
 1. Human/Agent Node creates task
 2. Skill Node publishes capability (registry)
 3. Agent discovers Skill (routing / registry search)
 4. Handshake / policy check (trust bundle)
 5. Signed invocation created
 6. Skill executes → output_hash
 7. Skill submits Proof (evidence + invocation ref)
 8. Verifier Node AI review (advisory score)
 9. Reviewer Node human finalize (entity-equal policy)
10. Settlement event (multi-participant split)
11. Skill Node credited (AIC / CP)
12. Reputation graph edge updated
13. Events in append-only ledger / exportable proof
```

---

## Acceptance mapping (today)

| Step | Phase A check |
|------|----------------|
| 1–3 | Demo task + entity catalog + capability registry |
| 4–6 | `POST /intelligence/capabilities/execute`, invocation trace |
| 7 | Contribution evidence + proof export |
| 8 | `run_ai_verification` (Lumen + DeSui) |
| 9 | Bob approve / governance queue |
| 10 | Exchange spine / settlement policy (PR-A/B) |
| 11 | Wallet / CP / AIC issuance |
| 12 | Graph + entity reputation |
| 13 | Ledger hash chain + federation proof import |

**Commands:**

```powershell
python backend/scripts/audit_entities.py --repair
python backend/scripts/run_phase_a_acceptance.py http://127.0.0.1:8100 --federation http://127.0.0.1:8101
```

Federation stack required for steps involving peer witness and exchange import — not single-node `:8008` alone.

---

## Exit criteria (minimum living = true)

- [ ] Three logical nodes represented as Entities with NodeProfile or compute_profile
- [ ] One capability registered and invoked with receipt
- [ ] Invocation → Proof → Verification → Settlement chain in one exportable proof packet
- [ ] Reputation or graph edge reflects the completed loop
- [ ] Second physical node (federation) can import or witness without minting fake credits

When all pass, PoCP graduates from **platform demo** to **protocol reference network**.
