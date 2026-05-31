"""Shared Ollama HTTP client — chat JSON witness + optional embeddings (NN-2)."""

from __future__ import annotations

import json
import os
import re

import httpx


def ollama_base_url() -> str:
    return os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")


def ollama_chat_model() -> str:
    return os.getenv("OLLAMA_MODEL", "llama3.2")


def ollama_embed_model() -> str:
    return os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")


def extract_json_object(text: str) -> dict:
    """Parse JSON from Ollama content, tolerating markdown fences."""
    raw = (text or "").strip()
    if not raw:
        raise ValueError("empty Ollama response")
    fence = re.match(r"^```(?:json)?\s*\n?(.*?)\n?```\s*$", raw, re.DOTALL | re.IGNORECASE)
    if fence:
        raw = fence.group(1).strip()
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("Ollama JSON response must be an object")
    return data


async def ollama_chat_json(
    *,
    messages: list[dict],
    model: str | None = None,
    timeout: float = 120,
) -> tuple[dict, str]:
    """Return (parsed_json, model_used)."""
    model = model or ollama_chat_model()
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(
            f"{ollama_base_url()}/api/chat",
            json={
                "model": model,
                "messages": messages,
                "stream": False,
                "format": "json",
            },
        )
        resp.raise_for_status()
        payload = resp.json()
    content = (payload.get("message") or {}).get("content") or ""
    return extract_json_object(content), model


def ollama_embed_sync(text: str, *, model: str | None = None, timeout: float = 30) -> list[float] | None:
    """Synchronous embedding for matching engine (optional NN-2 path)."""
    if not (text or "").strip():
        return None
    model = model or ollama_embed_model()
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(
                f"{ollama_base_url()}/api/embeddings",
                json={"model": model, "prompt": text.strip()},
            )
            resp.raise_for_status()
            embedding = resp.json().get("embedding")
            if isinstance(embedding, list) and embedding:
                return [float(x) for x in embedding]
    except Exception:
        return None
    return None
