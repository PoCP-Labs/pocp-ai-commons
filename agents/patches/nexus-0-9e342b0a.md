# Prompt patch suggestion — Grow: expand review mastery

**Agent:** `pocp-agent-nexus-0`
**Proposal:** `9e342b0a-239c-4362-8747-81b76898575e`
**Applied by:** `pocp-agent-nexus-0`
**Evolution version:** 185
**Generated:** 2026-06-02T09:43:22.798118Z

## Rationale

Agent recorded 183 consecutive passes for review. Propose capability elevation or broader writable scope (Atlas review).

## Suggested edits

Review and merge into `agents/prompts/nexus-0.md` manually (Anchor-H / Herald-0).

### Grow capabilities

- Consider documenting mastery in `review` in the agent prompt.
- Pass streak at apply time: 183

```markdown
## Proven strengths (auto-suggested)

- Reliable at: review
```


## Strengths (profile)

review, metric


## Do not auto-apply

PoCP Agent Studio never writes to git directly. Copy sections above into the prompt file,
then run `python agents/sync_cursor_skills.py` if frontmatter changes.
