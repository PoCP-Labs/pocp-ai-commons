# Prompt patch suggestion — Grow: expand test mastery

**Agent:** `pocp-agent-vault-0`
**Proposal:** `8ffb9a9c-279b-45da-aa5d-82c2eb1a6ffb`
**Applied by:** `pocp-agent-nexus-0`
**Evolution version:** 2
**Generated:** 2026-06-03T02:57:20.101251Z

## Rationale

Agent recorded 3 consecutive passes for test. Propose capability elevation or broader writable scope (Atlas review).

## Suggested edits

Review and merge into `agents/prompts/vault-0.md` manually (Anchor-H / Herald-0).

### Grow capabilities

- Consider documenting mastery in `test` in the agent prompt.
- Pass streak at apply time: 3

```markdown
## Proven strengths (auto-suggested)

- Reliable at: test
```


## Strengths (profile)

proof_packet, ledger_chain, wallet_audit, test


## Do not auto-apply

PoCP Agent Studio never writes to git directly. Copy sections above into the prompt file,
then run `python agents/sync_cursor_skills.py` if frontmatter changes.
