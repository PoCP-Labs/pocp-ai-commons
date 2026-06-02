"""OpenAI-compatible chat witness via vLLM — high-throughput community compute nodes."""

from __future__ import annotations

import json
import os

import httpx

from services.verifiers.base import BaseVerifier, VerifierResult
from services.llm_language import verifier_system_prompt
from services.verifiers.openai_verifier import build_verifier_prompt, normalize_result


class VllmVerifier(BaseVerifier):
    """Distributed compute adapter: vLLM OpenAI-compatible `/v1/chat/completions`."""

    provider_name = "vllm"

    def __init__(self):
        base = os.getenv("VLLM_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
        self.base_url = base
        self.model = os.getenv("VLLM_MODEL", "meta-llama/Meta-Llama-3-8B-Instruct")
        self.timeout = float(os.getenv("VLLM_TIMEOUT_SECONDS", "120"))

    @property
    def available(self) -> bool:
        return os.getenv("ENABLE_VLLM_VERIFIER", "false").lower() == "true"

    async def verify(self, context: dict) -> VerifierResult:
        if not self.available:
            raise RuntimeError("ENABLE_VLLM_VERIFIER is not true")

        prompt = build_verifier_prompt(context)
        url = f"{self.base_url}/v1/chat/completions"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": verifier_system_prompt()},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
        }
        headers = {"Content-Type": "application/json"}
        api_key = os.getenv("VLLM_API_KEY")
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

        content = data["choices"][0]["message"]["content"]
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            start = content.find("{")
            end = content.rfind("}")
            parsed = json.loads(content[start : end + 1]) if start >= 0 and end > start else {}
        model = data.get("model") or self.model
        return normalize_result(self.provider_name, model, parsed)
