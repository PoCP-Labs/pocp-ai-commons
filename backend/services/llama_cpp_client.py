"""llama.cpp server client helpers — OpenAI-compatible chat endpoint."""

from __future__ import annotations

import os


def llama_cpp_base_url() -> str:
    return os.getenv("LLAMA_CPP_BASE_URL", "http://127.0.0.1:8080").rstrip("/")


def llama_cpp_chat_model() -> str:
    return os.getenv("LLAMA_CPP_MODEL", "llama")


def llama_cpp_chat_enabled() -> bool:
    return os.getenv("ENABLE_LLAMA_CPP_CHAT", os.getenv("ENABLE_LLAMA_CPP_VERIFIER", "false")).lower() in (
        "true",
        "1",
        "yes",
        "on",
    )
