# Prompt patch suggestion — Grow: expand test mastery

**Agent:** `pocp-agent-sentinel-0`
**Proposal:** `f478d88f-76bf-4ea4-8fc2-6e9fa749a53b`
**Applied by:** `pocp-agent-nexus-0`
**Evolution version:** 1
**Generated:** 2026-06-03T01:22:00.190317Z

## Rationale

Agent recorded 3 consecutive passes for test. Propose capability elevation or broader writable scope (Atlas review).

## Suggested edits

Review and merge into `agents/prompts/sentinel-0.md` manually (Anchor-H / Herald-0).

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
