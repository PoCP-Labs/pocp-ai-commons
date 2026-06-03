# Prompt patch suggestion — Grow: expand test mastery

**Agent:** `pocp-agent-compass-0`
**Proposal:** `bc74eac1-7f0f-4818-be17-07a15679c690`
**Applied by:** `pocp-agent-nexus-0`
**Evolution version:** 2
**Generated:** 2026-06-02T08:29:01.879257Z

## Rationale

Agent recorded 4 consecutive passes for test. Propose capability elevation or broader writable scope (Atlas review).

## Suggested edits

Review and merge into `agents/prompts/compass-0.md` manually (Anchor-H / Herald-0).

### Grow capabilities

- Consider documenting mastery in `test` in the agent prompt.
- Pass streak at apply time: 4

```markdown
## Proven strengths (auto-suggested)

- Reliable at: test
```


## Strengths (profile)

roadmap_planning, issue_triage, pilot_metrics, test


## Do not auto-apply

PoCP Agent Studio never writes to git directly. Copy sections above into the prompt file,
then run `python agents/sync_cursor_skills.py` if frontmatter changes.
