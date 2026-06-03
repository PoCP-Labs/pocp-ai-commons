# Prompt patch suggestion — Grow: expand review mastery

**Agent:** `pocp-agent-nexus-0`
**Proposal:** `77c6ee7f-83b5-4049-89de-3b3a5da4d6d4`
**Applied by:** `pocp-agent-nexus-0`
**Evolution version:** 153
**Generated:** 2026-06-02T08:57:43.942746Z

## Rationale

Agent recorded 170 consecutive passes for review. Propose capability elevation or broader writable scope (Atlas review).

## Suggested edits

Review and merge into `agents/prompts/nexus-0.md` manually (Anchor-H / Herald-0).

### Grow capabilities

- Consider documenting mastery in `review` in the agent prompt.
- Pass streak at apply time: 170

```markdown
## Proven strengths (auto-suggested)

- Reliable at: review
```


## Strengths (profile)

review, metric


## Do not auto-apply

PoCP Agent Studio never writes to git directly. Copy sections above into the prompt file,
then run `python agents/sync_cursor_skills.py` if frontmatter changes.
