# Prompt patch suggestion — Grow: expand test mastery

**Agent:** `pocp-agent-atlas-0`
**Proposal:** `15b5b98d-26dd-4a70-bed1-4bf41eac48a9`
**Applied by:** `pocp-agent-nexus-0`
**Evolution version:** 1
**Generated:** 2026-06-02T09:06:35.702191Z

## Rationale

Agent recorded 3 consecutive passes for test. Propose capability elevation or broader writable scope (Atlas review).

## Suggested edits

Review and merge into `agents/prompts/atlas-0.md` manually (Anchor-H / Herald-0).

### Grow capabilities

- Consider documenting mastery in `test` in the agent prompt.
- Pass streak at apply time: 3

```markdown
## Proven strengths (auto-suggested)

- Reliable at: test
```


## Strengths (profile)

test


## Do not auto-apply

PoCP Agent Studio never writes to git directly. Copy sections above into the prompt file,
then run `python agents/sync_cursor_skills.py` if frontmatter changes.
