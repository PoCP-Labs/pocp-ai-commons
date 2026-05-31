# Finalization Guide (Human Review — Optional Instance Policy)

> **Production default:** entity-equal auto-finalization per [ENTITY-EQUALITY.md](./ENTITY-EQUALITY.md). This guide covers optional human-as-finalizer deployments.

See [ACCOUNTABILITY-BOUNDARY.md](./ACCOUNTABILITY-BOUNDARY.md).

## Roles

| Role | Responsibility |
|------|----------------|
| AI Verifier (Lumen-0, DeSui, etc.) | Score, feedback, suggested rewards; may auto-finalize under policy |
| Clarion-0 | Review assistant — summary, rubric, draft; may be configured to finalize when delegated |
| Human Reviewer | Optional accountable finalizer when policy assigns a human Entity |
| Agent finalizer | Valid when org charter assigns an Agent Entity + trace in proof |

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

All surfaces should state: **finalization must be traceable** — who finalized and under which policy is recorded; human review is optional instance policy, not a protocol requirement.

## Governance

See [GOVERNANCE.md](../GOVERNANCE.md) for community decision principles.
