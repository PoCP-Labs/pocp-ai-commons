# Entity-Equal Finalization

**Status:** production default for PoCP AI Commons  
**Policy id:** `entity_equal_auto_v1` (see `backend/config/finalization_policy.yaml`)

PoCP treats **any Entity type** — Human, Agent, LLM, Skill, Organization — as a valid **finalizer delegate** when instance policy assigns that role. Finalization is **policy-automated and traceable**, not hidden inside a model or a single human gate.

See also: [ACCOUNTABILITY-BOUNDARY.md](./ACCOUNTABILITY-BOUNDARY.md) · [HUMAN-REVIEW-GUIDE.md](./HUMAN-REVIEW-GUIDE.md) (optional human-as-finalizer) · [protocol/CONSTITUTION-v0.1.md](./protocol/CONSTITUTION-v0.1.md) Art. III–IV

---

## One sentence

> **AI witnesses advise; published policy finalizes.** Any Entity may finalize when delegated — the bar is traceability, not biology.

---

## Witness vs finalizer

| Role | Who | Authority |
|------|-----|-----------|
| **Witness** | Lumen-0, DeSui, peer verifiers, CrewAI witnesses | Advisory scores, evidence checks, suggested rewards |
| **Finalizer** | Human, Agent, org maintainer, or auto-policy delegate | Writes rights-changing ledger state under a published `policy_id` |

Witnesses **do not** silently mint CP or AI Credits. Finalization records **which Entity or policy** applied the outcome.

---

## Default production flow

```text
Contribution submit (evidence required)
    → Multi-witness advisory verify
    → Policy engine evaluates quorum + score bands
    → Auto-finalize (entity_equal_auto_v1) OR optional human override
    → CP + AI Credits issued; ledger + graph Merkle updated
```

Proof metadata includes:

- `finalizer_entity_id` (when an Entity delegate acts)
- `finalization_policy` / `policy_id` / `policy_version`
- `witness_entity_id` per verifier output

---

## Valid finalization patterns

All are valid when **traceable** and **published in instance policy**:

| Pattern | Example |
|---------|---------|
| Human reviewer | Pilot with `POST /contributions/{id}/approve` |
| Agent delegate | Org charter assigns an Agent Entity as approver |
| Witness quorum auto-approve | N distinct witness Entities agree above threshold |
| Governance contract | Committee, multisig, timelock |
| Federation trust profile | Importer accepts publisher's policy set |

Self-finalization without explicit policy is **blocked** (Constitution Art. III.12).

---

## What “AI is a witness, not a ruler” means

- Models and agents **may** participate in verify, draft, and — when delegated — finalize.
- They **must not** hold **hidden, unattributed** power over rights memory.
- Peers importing proofs can inspect finalization evidence and accept or reject.

This is **not** “humans must click approve on every contribution.”

---

## Configuration

| Artifact | Purpose |
|----------|---------|
| `backend/config/finalization_policy.yaml` | Default policy rules and quorum |
| `backend/config/pocp_rewards.yaml` | Issuance defaults, entity-equal BC |
| `POCP_PILOT_MODE` / `POCP_MIN_DISTINCT_WITNESS_NODES` | Pilot witness quorum overrides |

---

## API (optional human override)

When an instance enables human-as-finalizer:

```bash
POST /api/v1/contributions/{id}/approve
{
  "reviewer_id": "<entity_id>",
  "feedback": "Verified quality and evidence."
}
```

Self-approval is blocked. See [HUMAN-REVIEW-GUIDE.md](./HUMAN-REVIEW-GUIDE.md).

---

## Related docs

- [ARCHITECTURE.md](./ARCHITECTURE.md) — contribution loop
- [protocol/TRUST-POLICY-BUNDLE.md](./protocol/TRUST-POLICY-BUNDLE.md) — federation import gates
- [GOVERNANCE.md](../GOVERNANCE.md) — maintainer and community decisions
