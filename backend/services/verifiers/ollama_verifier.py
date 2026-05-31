import os

from services.ollama_client import ollama_chat_json, ollama_chat_model
from services.verifiers.base import BaseVerifier, VerifierResult
from services.verifiers.openai_verifier import build_verifier_prompt, normalize_result


class OllamaVerifier(BaseVerifier):
    """Local LLM witness via Ollama — federation-friendly, no cloud API key."""

    provider_name = "ollama"

    def __init__(self):
        self.model = ollama_chat_model()

    @property
    def available(self) -> bool:
        return os.getenv("ENABLE_OLLAMA_VERIFIER", "false").lower() == "true"

    async def verify(self, context: dict) -> VerifierResult:
        if not self.available:
            raise RuntimeError("ENABLE_OLLAMA_VERIFIER is not true")

        prompt = build_verifier_prompt(context)
        data, model = await ollama_chat_json(
            messages=[
                {
                    "role": "system",
                    "content": "You are an AI advisory verifier for PoCP AI Commons. Return JSON only.",
                },
                {"role": "user", "content": prompt},
            ],
            model=self.model,
        )
        return normalize_result(self.provider_name, model, data)
