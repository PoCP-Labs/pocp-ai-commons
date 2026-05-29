# Review Guide

PoCP AI Commons uses human review to protect quality, safety, and alignment.

AI may assist review, but humans make final decisions.

## What reviewers should check

### 1. Correctness

- Does the code solve the issue?
- Does it meet acceptance criteria?
- Does it handle errors?
- Does it keep existing behavior working?

### 2. Scope

- Is the change too large?
- Does it rewrite unrelated parts?
- Does it introduce unnecessary dependencies?
- Does it add features not requested?

### 3. Security

- Are secrets exposed?
- Is authentication handled safely?
- Are user inputs validated?
- Could this enable abuse?
- Does it affect AI Credits or wallet logic?

### 4. PoCP alignment

Check that the PR respects:

- AI is advisory, not final authority.
- Human reviewers remain responsible.
- No token-first behavior.
- No speculative financial promises.
- Contribution records remain transparent.
- Credits are usage rights, not investment assets.

### 5. Tests

- Are tests included?
- Are smoke test steps provided?
- Can the reviewer reproduce the behavior?
- Are error cases tested?

### 6. Documentation

- Does README need updates?
- Does API documentation need updates?
- Does the user flow change?

## Review comments

Good review comments should be:

- specific;
- actionable;
- respectful;
- tied to acceptance criteria;
- focused on the code, not the person.

## AI-assisted review

Reviewers may use AI to:

- summarize a PR;
- identify possible bugs;
- compare code with acceptance criteria;
- draft review comments;
- check docs consistency.

But AI cannot approve a PR by itself.

## Conflict of interest

Reviewers should not approve their own contributions.

If the reviewer helped generate a patch, another human should review before merge.

## Merge principle

A PR can be merged when:

- it solves a defined issue;
- acceptance criteria are met;
- tests or manual verification are clear;
- risks are acceptable;
- documentation is updated if needed;
- at least one accountable human maintainer approves.

PoCP begins with contribution.
