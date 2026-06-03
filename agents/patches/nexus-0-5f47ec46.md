# Prompt patch suggestion — Grow: expand review mastery

**Agent:** `pocp-agent-nexus-0`
**Proposal:** `5f47ec46-caf0-4654-abd0-61f97644fd64`
**Applied by:** `pocp-agent-nexus-0`
**Evolution version:** 221
**Generated:** 2026-06-03T01:20:00.572441Z

## Rationale

Agent recorded 204 consecutive passes for review. Propose capability elevation or broader writable scope (Atlas review).

## Suggested edits

Review and merge into `agents/prompts/nexus-0.md` manually (Anchor-H / Herald-0).

### Grow capabilities

- Consider documenting mastery in `review` in the agent prompt.
- Pass streak at apply time: 204

```markdown
## Proven strengths (auto-suggested)

- Reliable at: review
```


## Strengths (profile)

review, metric


## Do not auto-apply

PoCP Agent Studio never writes to git directly. Copy sections above into the prompt file,
then run `python agents/sync_cursor_skills.py` if frontmatter changes.
