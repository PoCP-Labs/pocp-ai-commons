"""vLLM server client helpers — OpenAI-compatible chat endpoint."""

from __future__ import annotations

import os


def vllm_base_url() -> str:
    return os.getenv("VLLM_BASE_URL", "http://127.0.0.1:8000").rstrip("/")


def vllm_chat_model() -> str:
    return os.getenv("VLLM_MODEL", "meta-llama/Meta-Llama-3-8B-Instruct")


def vllm_chat_enabled() -> bool:
    explicit = os.getenv("ENABLE_VLLM_CHAT", "").strip().lower()
    if explicit in ("true", "1", "yes", "on"):
        return True
    if explicit in ("false", "0", "no", "off"):
        return False
    return os.getenv("ENABLE_VLLM_VERIFIER", "false").lower() in ("true", "1", "yes", "on")
