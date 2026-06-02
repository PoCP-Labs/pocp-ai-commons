---
name: Review Task
about: Review code, spec, prompt, Skill, or AI-generated output
title: "[Review] "
labels: "review"
assignees: ""
---

## What needs review?

Link PR, issue, spec, or document.

## Phase & verification

| Field | Value |
|-------|-------|
| **Phase** | A · B · C (see [ROADMAP-THREE-PHASES.md](../../docs/ROADMAP-THREE-PHASES.md)) |
| **Acceptance command** | PR author's test plan + `run_phase_a_acceptance.py` when code changes |

## Review focus

- [ ] Correctness
- [ ] Security
- [ ] AI-generated code quality
- [ ] PoCP alignment
- [ ] Tests
- [ ] Documentation
- [ ] Anti-abuse
- [ ] User experience

## Expected output

- [ ] Review comment
- [ ] Approval
- [ ] Change request
- [ ] Risk note
- [ ] Suggested patch

## Notes

AI can assist review, but humans remain responsible for final decisions.
