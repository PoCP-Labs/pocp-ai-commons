# Anchor-H — Human anchor

**entity_id:** your registered human Entity (e.g. from login / entity register API)  
**Not an AI agent.**

## Exclusive powers

- Production/staging secrets and GitHub OAuth app credentials.
- Staging deploy and public pilot go-live.
- Contribution disputes when policy cannot auto-finalize.
- External statements on tokens, partnerships, liability.

## When Meta agents must stop and ask you

- Any credential, billing, or legal exposure.
- Acceptance green but high-risk pilot launch.
- Atlas vs Vault disagreement on issuance — you decide go-live; Atlas decides schema.

## Checklist before staging

- [ ] `backend/.env` on server — not in git
- [ ] `ENABLE_DEV_LOGIN=false`
- [ ] `run_phase_a_acceptance.py` with `--staging` green
- [ ] Lex-0 PASS on README/UI/issue templates for this release
- [ ] NO token/investment promises in release notes

## For humans using Cursor

Start session as yourself; delegate to **Nexus-0** (`agents/prompts/nexus-0.md`) for implementation work.
