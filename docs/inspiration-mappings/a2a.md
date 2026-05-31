# A2A → PoCP Intelligence Layer

**Source:** [a2aproject/A2A](https://github.com/a2aproject/A2A) · Benchmark: [DISTRIBUTED-INTELLIGENCE-BENCHMARK.md](../DISTRIBUTED-INTELLIGENCE-BENCHMARK.md)

## What to borrow

| A2A concept | PoCP mapping |
|-------------|--------------|
| Agent Card (`/.well-known/agent.json`) | Per-Entity capability manifest + ComputeProfile |
| `SendMessage` (JSON-RPC) | Creates `ContributionEvent` + participants |
| `GetTask` / `ListTasks` | Maps contribution status → A2A task state |
| Cross-framework delegation | Target Entity added as executor / skill_provider / … |

## What to reject

- Using A2A task `TASK_STATE_COMPLETED` without human approval
- Skipping evidence / contribution binding
- Agent Card as sole identity — PoCP Entity + owner remains canonical

## Endpoints (shipped)

| Endpoint | Purpose |
|----------|---------|
| `GET /.well-known/agent.json` | Node Agent Card (A2A discovery) |
| `GET /api/v1/intelligence/agent-card` | Same as well-known |
| `GET /api/v1/intelligence/entities/{id}/agent-card` | Per-Entity Agent Card |
| `POST /api/v1/intelligence/a2a` | Node JSON-RPC (`SendMessage`, `GetTask`, …) |
| `POST /api/v1/intelligence/entities/{id}/a2a` | Entity-scoped JSON-RPC |
| `GET …/a2a` | Service descriptor + method list |

## JSON-RPC example

```bash
TOKEN=…  # from /api/v1/auth/dev-login

curl -X POST http://localhost:8000/api/v1/intelligence/entities/{agent_id}/a2a \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "SendMessage",
    "params": {
      "message": {
        "role": "ROLE_USER",
        "parts": [{"kind": "text", "text": "Document this API change with evidence."}]
      },
      "metadata": {
        "taskId": "{pocp_task_uuid}",
        "contributionType": "knowledge",
        "contextId": "ctx-demo-1"
      }
    }
  }'
```

Response `result.task.id` is the **contribution id**. Run verification:

```bash
curl -X POST http://localhost:8000/api/v1/contributions/{contribution_id}/auto-verify \
  -H "Authorization: Bearer $TOKEN"
```

## Task state mapping

| PoCP `ContributionStatus` | A2A `state` |
|---------------------------|-------------|
| `submitted` | `TASK_STATE_SUBMITTED` |
| `ai_verified` | `TASK_STATE_INPUT_REQUIRED` (policy finalization pending) |
| `approved` | `TASK_STATE_COMPLETED` |
| `rejected` | `TASK_STATE_REJECTED` |

## Code

- `backend/services/a2a_agent_card.py` — Agent Card builder (BI-1)
- `backend/services/a2a_task_bridge.py` — JSON-RPC handler (BI-1.5)
- `backend/services/contribution_submit.py` — shared submission helper

## Status

**active (BI-1 + BI-1.5)** — registry entry `a2a_protocol` in `neural_network_sources.yaml`.

Not yet implemented: `SendStreamingMessage`, `CancelTask`, JSON-RPC batch, blocking `returnImmediately: false` auto-verify loop.
