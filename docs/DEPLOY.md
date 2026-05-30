# PoCP AI Commons — Deployment & Configuration Guide

## Quick Start

```bash
# 1. Start everything
docker compose up --build

# 2. Access
#    Frontend:  http://localhost:3000
#    API docs:  http://localhost:8000/docs
#    Health:    http://localhost:8000/health
```

## Environment Variables

All optional. Defaults work for local development.

### AI Model Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `AI_API_KEY` | `` (empty) | API key for OpenAI-compatible provider. If empty, chat uses simulated replies. |
| `AI_API_BASE` | `https://api.deepseek.com/v1` | API base URL. Change to `https://api.openai.com/v1` for OpenAI, or `http://localhost:11434/v1` for local Ollama. |
| `AI_MODEL` | `deepseek-chat` | Model name. Supports `gpt-4o`, `deepseek-chat`, `qwen`, or any model available at your API endpoint. |
| `AI_TIMEOUT` | `30` | API request timeout in seconds. |

### Examples

**DeepSeek** (default, cheap and capable):
```bash
AI_API_KEY=sk-your-deepseek-key
```

**OpenAI GPT-4o**:
```bash
AI_API_BASE=https://api.openai.com/v1
AI_API_KEY=sk-your-openai-key
AI_MODEL=gpt-4o
```

**Local Ollama**:
```bash
AI_API_BASE=http://localhost:11434/v1
AI_API_MODEL=qwen2.5
```

### Auth Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | Auto-generated | JWT signing secret. Set a fixed value for production. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Access token lifetime. |

## Docker Compose

```yaml
# Add AI config to docker-compose.yml
services:
  backend:
    environment:
      - AI_API_KEY=${AI_API_KEY:-}
      - AI_API_BASE=${AI_API_BASE:-https://api.deepseek.com/v1}
      - AI_MODEL=${AI_MODEL:-deepseek-chat}
```

Or use a `.env` file:

```bash
echo "AI_API_KEY=sk-your-key" >> .env
echo "AI_MODEL=deepseek-chat" >> .env
docker compose up --build
```

## Verification

```bash
# Test chat endpoint
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"entity_id": "<your-entity-id>", "message": "What is PoCP?"}'

# Test health
curl http://localhost:8000/health
```
