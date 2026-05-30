# Human Review Guide

Human reviewers make **final** approval decisions. AI verifiers are witnesses, not rulers.

## Roles

| Role | Responsibility |
|------|----------------|
| AI Verifier (Lumen-0, DeSui, etc.) | Advisory score, feedback, suggested rewards |
| Clarion-0 | Reviewer assistant — summary, rubric, questions (advisory) |
| Human Reviewer | Final approve / reject / request changes |

## Approval flow

```bash
# After auto-verify
POST /api/v1/contributions/{id}/approve
{
  "reviewer_id": "<human_entity_id>",
  "feedback": "Verified quality and evidence."
}
```

## Rules (Sprint Alpha)

- **Self-approval blocked** — reviewer cannot be the primary contributor
- Evidence required on submission
- Daily contribution limits enforced
- AI verification is advisory only — status remains until human acts

## Clarion-0 assistant

```bash
GET /api/v1/contributions/{id}/clarion-review
Authorization: Bearer <reviewer_token>
```

Returns advisory packet: summary, concerns, reviewer questions, suggested rewards. Does not approve.

## UI messaging

All surfaces should state: **AI is advisory only. Human reviewers make final decisions.**

## Governance

See [GOVERNANCE.md](../GOVERNANCE.md) for community decision principles.
