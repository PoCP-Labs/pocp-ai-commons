# Verifier Adapter Guide

AI verifiers provide **advisory** contribution review. They never auto-approve.

## Architecture

```
services/verifiers/
  base.py           — BaseVerifier interface
  mock_verifier.py  — Local fallback (no API key)
  openai_verifier.py
  deepseek_verifier.py
  multi_verifier.py — Consensus aggregation
```

## Flow

1. Contributor submits contribution with evidence
2. Client calls `POST /api/v1/contributions/{id}/auto-verify`
3. MultiVerifier runs configured adapters (OpenAI, DeepSeek, Mock)
4. Consensus score + structured feedback stored
5. **Human reviewer** calls `approve` for final decision

## Configuration

```env
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini
DEEPSEEK_API_KEY=
DEEPSEEK_MODEL=deepseek-chat
ENABLE_MOCK_VERIFIER=true
```

When API keys are missing, Mock verifier ensures the loop still works locally.

## Adding a verifier

1. Subclass `BaseVerifier` in `services/verifiers/`
2. Implement `verify(contribution, context) -> VerifierResult`
3. Register in `multi_verifier.py`
4. Return structured JSON: score, passed (advisory), feedback, suggested CP/Credits

## Guardrails

- Verifiers must not call `approve_contribution`
- Manual verify endpoint disabled by default
- All outputs labeled advisory in API and UI

See [Human Review Guide](./HUMAN-REVIEW-GUIDE.md).
