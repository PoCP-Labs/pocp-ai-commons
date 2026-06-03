# Prompt patch suggestion — Grow: expand review mastery

**Agent:** `pocp-agent-nexus-0`
**Proposal:** `dd91b5d4-443c-4f94-8025-e8de36659f34`
**Applied by:** `pocp-agent-nexus-0`
**Evolution version:** 229
**Generated:** 2026-06-03T01:24:35.729805Z

## Rationale

Agent recorded 207 consecutive passes for review. Propose capability elevation or broader writable scope (Atlas review).

## Suggested edits

Review and merge into `agents/prompts/nexus-0.md` manually (Anchor-H / Herald-0).

### Grow capabilities

- Consider documenting mastery in `review` in the agent prompt.
- Pass streak at apply time: 207

```markdown
## Proven strengths (auto-suggested)

- Reliable at: review
```


## Strengths (profile)

review, metric


## Do not auto-apply

PoCP Agent Studio never writes to git directly. Copy sections above into the prompt file,
then run `python agents/sync_cursor_skills.py` if frontmatter changes.
