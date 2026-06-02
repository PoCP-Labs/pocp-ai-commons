# Prompt patch suggestion — Improve after fail: acceptance

**Agent:** `pocp-agent-vault-0`
**Proposal:** `c2bf30ad-9b19-40b2-a3be-562c04f2b36f`
**Applied by:** `pocp-agent-nexus-0`
**Evolution version:** 1
**Generated:** 2026-06-01T23:57:48.086110Z

## Rationale

acceptance runner red on wallet audit

## Suggested edits

Review and merge into `agents/prompts/vault-0.md` manually (Anchor-H / Herald-0).

### Improve playbook

- Add a **Failure recovery** section referencing this outcome evidence.
- Tighten pre-merge checklist for the failing domain.
- Evidence keys: `[]`

```markdown
## Failure recovery (auto-suggested)

- Last failure context: Improve after fail: acceptance
- Re-run tests listed in handoff before returning to Nexus-0.
```

## Growth areas (profile)

workflow_update


## Do not auto-apply

PoCP Agent Studio never writes to git directly. Copy sections above into the prompt file,
then run `python agents/sync_cursor_skills.py` if frontmatter changes.
