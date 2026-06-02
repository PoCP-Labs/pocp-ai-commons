# Prompt patch suggestion — Improve after fail: test

**Agent:** `pocp-agent-gauge-0`
**Proposal:** `a6f457db-cfdb-474d-8e8c-487760fdab20`
**Applied by:** `pocp-agent-nexus-0`
**Evolution version:** 1
**Generated:** 2026-06-01T04:26:02.946218Z

## Rationale

ci red

## Suggested edits

Review and merge into `agents/prompts/gauge-0.md` manually (Anchor-H / Herald-0).

### Improve playbook

- Add a **Failure recovery** section referencing this outcome evidence.
- Tighten pre-merge checklist for the failing domain.
- Evidence keys: `[]`

```markdown
## Failure recovery (auto-suggested)

- Last failure context: Improve after fail: test
- Re-run tests listed in handoff before returning to Nexus-0.
```

## Growth areas (profile)

prompt_refine


## Do not auto-apply

PoCP Agent Studio never writes to git directly. Copy sections above into the prompt file,
then run `python agents/sync_cursor_skills.py` if frontmatter changes.
