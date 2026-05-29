# AI-Assisted Coding Guide

PoCP AI Commons welcomes AI-assisted development.

Humans, Agents, LLMs, and Skills can all participate in the code production chain.

However, AI-generated code must be reviewed by accountable humans before merge.

## Allowed AI assistance

You may use AI tools to:

- generate draft code;
- explain existing code;
- write tests;
- refactor small modules;
- draft documentation;
- generate API examples;
- write Cursor prompts;
- review code for risks;
- translate docs.

## Required human responsibility

Before submitting AI-assisted code, the human contributor should:

- read the generated code;
- understand what it does;
- run or explain tests;
- check security and privacy risks;
- ensure it matches the issue;
- remove hallucinated dependencies or files;
- disclose AI assistance when relevant.

## Recommended workflow

```text
Issue
→ Acceptance Criteria
→ Cursor / Agent Prompt
→ Generated Patch
→ Human Review
→ Test
→ PR
→ Maintainer Review
```

## Prompt template for Cursor

```text
You are working in PoCP-Labs/pocp-ai-commons.

Task:
[describe the issue]

Constraints:
- Do not rewrite the whole project.
- Keep existing demo and seed data working.
- Do not introduce blockchain, token, or DAO.
- Keep AI advisory; humans make final decisions.
- Add tests or smoke test steps.
- Update docs if behavior changes.

Acceptance criteria:
- [criterion 1]
- [criterion 2]
- [criterion 3]

Please implement minimal changes and explain how to test.
```

## AI-generated code disclosure

In your PR, include:

```markdown
## AI Assistance Disclosure

This PR was drafted with AI assistance and reviewed by the human contributor before submission.
```

## Agent contribution attribution

If an Agent or Skill meaningfully contributed, mention it:

```markdown
Agent / Skill used:
- Cursor
- Lumen-0（明证）
- Code Review Skill
```

## What AI should not do alone

AI should not independently:

- approve PRs;
- merge code;
- change governance rules;
- assign CP or Credits without human review;
- introduce authentication or security logic without human review;
- handle secrets;
- decide final contribution value.

## Principle

AI can accelerate coding.

Humans remain responsible for meaning, safety, and final judgment.

PoCP begins with contribution.
