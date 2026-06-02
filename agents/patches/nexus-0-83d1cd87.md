# Prompt patch suggestion — Grow: expand review mastery

**Agent:** `pocp-agent-nexus-0`
**Proposal:** `83d1cd87-7c23-4f66-a3fa-70c8282a747f`
**Applied by:** `pocp-agent-nexus-0`
**Evolution version:** 1
**Generated:** 2026-06-02T00:14:53.925897Z

## Rationale

Agent recorded 72 consecutive passes for review. Propose capability elevation or broader writable scope (Atlas review).

## Suggested edits

Review and merge into `agents/prompts/nexus-0.md` manually (Anchor-H / Herald-0).

### Grow capabilities

- Consider documenting mastery in `review` in the agent prompt.
- Pass streak at apply time: 72

```markdown
## Proven strengths (auto-suggested)

- Reliable at: review
```


## Strengths (profile)

review


## Do not auto-apply

PoCP Agent Studio never writes to git directly. Copy sections above into the prompt file,
then run `python agents/sync_cursor_skills.py` if frontmatter changes.
