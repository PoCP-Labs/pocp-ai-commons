# Prompt patch suggestion — Grow: expand test mastery

**Agent:** `pocp-agent-atlas-0`
**Proposal:** `d6d943d6-e027-4bc7-9253-2c936d69e8f4`
**Applied by:** `pocp-agent-nexus-0`
**Evolution version:** 3
**Generated:** 2026-06-02T09:43:22.549974Z

## Rationale

Agent recorded 4 consecutive passes for test. Propose capability elevation or broader writable scope (Atlas review).

## Suggested edits

Review and merge into `agents/prompts/atlas-0.md` manually (Anchor-H / Herald-0).

### Grow capabilities

- Consider documenting mastery in `test` in the agent prompt.
- Pass streak at apply time: 4

```markdown
## Proven strengths (auto-suggested)

- Reliable at: test
```


## Strengths (profile)

test


## Do not auto-apply

PoCP Agent Studio never writes to git directly. Copy sections above into the prompt file,
then run `python agents/sync_cursor_skills.py` if frontmatter changes.
