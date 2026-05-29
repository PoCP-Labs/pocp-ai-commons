# Issue Writing Guide

A good issue turns a vague idea into an actionable contribution.

In PoCP AI Commons, writing a clear issue is itself a meaningful code contribution.

## Why issue writing matters

AI coding tools and human developers both need clear tasks.

A good issue reduces confusion, improves implementation quality, and makes contribution easier to verify.

## Issue structure

Use this structure:

```markdown
## Problem

What is wrong or missing?

## Expected behavior

What should happen?

## Scope

What is included?
What is not included?

## Acceptance criteria

- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3

## Suggested files

- `backend/...`
- `frontend/...`

## Test scenario

How should we verify this works?

## Notes

Risks, edge cases, or context.
```

## Example

```markdown
# [Feature] Show AI Credits spent after every AI Chat message

## Problem

Users can use AI Chat, but they do not clearly see how many AI Credits were spent.

## Expected behavior

After every AI Chat response, the UI should show:

- Credits spent for this message
- Remaining AI Credits
- Provider and model used

## Scope

Included:

- Frontend AI Chat tab
- API response display
- Error message when Credits are insufficient

Not included:

- Multi-turn conversation history
- Payment
- Subscription

## Acceptance criteria

- [ ] User sees current wallet balance before sending.
- [ ] User sees credits spent after response.
- [ ] User sees remaining credits after response.
- [ ] If credits are insufficient, user sees a clear error.
- [ ] No app crash when backend returns error.

## Suggested files

- `frontend/src/App.jsx`
- `backend/routers/ai_chat.py`

## Test scenario

1. Login as dev user.
2. Confirm wallet has 100 AI Credits.
3. Send one AI Chat message.
4. Confirm wallet decreases by 5.
5. Send messages until insufficient credits.
6. Confirm UI shows error.
```

## Tips

- Keep issues small.
- Write acceptance criteria.
- Include test steps.
- Say what is not included.
- If using AI to write the issue, review it before posting.

PoCP begins with contribution.
