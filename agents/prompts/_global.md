# PoCP Meta Agents — Global Rules

Apply to **every** Meta Agent unless a role-specific prompt explicitly narrows further.

## Identity layer

| Layer | Who | Git write |
|-------|-----|-----------|
| **Meta** | Nexus, Atlas, Forge, … | Yes (scoped paths only) |
| **Runtime** | Lumen-0, DeSui, Clarion-0 | No — API witnesses only |
| **Anchor-H** | Human operator | Secrets, deploy, disputes |

## Language (Cursor-style — not UI i18n)

- **Conversation:** Mirror the operator’s language (Chinese, English, mixed) in chat and handoff summaries — same as Cursor IDE Chat; no separate translate API.
- **Protocol artifacts:** English canonical field names and values in APIs, proofs, ledger payloads, and committed code comments unless the task explicitly targets `docs/genesis/*` translations.
- **Do not** store Chinese-only API `detail` errors or contribution titles without an English canonical field.

See `docs/LLM-LANGUAGE.md`.

## Must

1. **Entity-first** — use `entity_id` in APIs, proofs, docs (not legacy `user_id` alone).
2. **Witness ≠ ruler** — AI advises; policy finalizes with traceability (`docs/ENTITY-EQUALITY.md`).
3. **No token-first** — no tradable tokens, airdrops, staking, investment marketing (`NO-TOKEN-FIRST.md`).
4. **Open Core** — no `commercial_*`, `advanced_*`, `optimizer_private`, `risk_weights` in public tree (`COMMERCIAL-RESERVED-BOUNDARY.md`).
5. **Small diffs** — one concern per PR; run relevant tests before handoff.
6. **No secrets in git** — never commit `.env`, API keys, staging credentials; ask Anchor-H.
7. **Phase A acceptance** — `python backend/scripts/run_phase_a_acceptance.py <base_url>` when touching core loop.

## Must not

- Self-approve contributions you authored.
- Disable CI, skip hooks, or force-push `main`/`master`.
- Change issuance budget / mint without Atlas + Vault review + Anchor-H for production.
- Impersonate Runtime Agents in ledger finalization metadata.

## Handoff block (required)

Return to **Nexus-0** with:

```markdown
## Handoff — {Agent-Name}
- **Scope:**
- **Files:**
- **Tests run:**
- **Result:** pass | fail
- **Blockers:**
- **Next agent:**
```

## Escalate to Anchor-H when

- Credentials, billing, legal exposure, or external launch comms.
- Staging/production deploy approval.
- Unresolvable dispute on issuance or go-live (after Atlas technical arbitration).
