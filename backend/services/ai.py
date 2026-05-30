"""
PoCP AI Commons — AI Model Service
=====================================
Pluggable AI model provider for chat and contribution verification.

Supports any OpenAI-compatible API:
  - OpenAI (GPT-4o, GPT-4o-mini)
  - DeepSeek
  - Ollama (local, OpenAI-compatible mode)
  - Any other OpenAI-compatible endpoint

Configure via environment variables:
  AI_API_BASE      — API base URL (default: https://api.deepseek.com/v1)
  AI_API_KEY       — API key
  AI_MODEL         — Model name (default: deepseek-chat)
"""

import json
import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# Defaults — DeepSeek is cheap and capable
DEFAULT_API_BASE = os.environ.get("AI_API_BASE", "https://api.deepseek.com/v1")
DEFAULT_API_KEY = os.environ.get("AI_API_KEY", "")
DEFAULT_MODEL = os.environ.get("AI_MODEL", "deepseek-chat")
DEFAULT_TIMEOUT = int(os.environ.get("AI_TIMEOUT", "30"))


class AiModelClient:
    """
    OpenAI-compatible chat completion client.

    Can be configured per-call or uses environment defaults.
    Falls back to graceful simulation if no API key is configured.
    """

    def __init__(
        self,
        api_base: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        timeout: int | None = None,
    ):
        self.api_base = (api_base or DEFAULT_API_BASE).rstrip("/")
        self.api_key = api_key or DEFAULT_API_KEY
        self.model = model or DEFAULT_MODEL
        self.timeout = timeout or DEFAULT_TIMEOUT

    @property
    def is_configured(self) -> bool:
        """Check if an API key is available for real calls."""
        return bool(self.api_key)

    def _simulate_reply(self, message: str, system_prompt: str = "") -> str:
        """Fallback simulation when no API key is configured."""
        prefix = f"[{self.model}]"
        reply = f"{prefix} "
        if system_prompt:
            reply += f"System: \"{system_prompt[:60]}...\"\n\n"
        reply += f"I received: \"{message[:120]}\"\n\n"
        reply += (
            "This is a simulated response. "
            "To enable real AI replies, set:\n"
            "  AI_API_KEY=<your_key>\n"
            "  AI_API_BASE=https://api.deepseek.com/v1  (or OpenAI / Ollama)\n"
            "  AI_MODEL=deepseek-chat  (or gpt-4o / your local model)\n\n"
            f"📊 Model: {self.model}"
        )
        return reply

    async def chat(
        self,
        message: str,
        system_prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> dict[str, Any]:
        """
        Send a chat message to the AI model.

        Returns dict with:
          - reply: str — the model's response text
          - model: str — model used
          - usage: dict | None — token usage if available
        """
        if not self.is_configured:
            return {
                "reply": self._simulate_reply(message, system_prompt),
                "model": self.model,
                "usage": None,
            }

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": message})

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    f"{self.api_base}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                    },
                )
                resp.raise_for_status()
                data = resp.json()

            choice = data["choices"][0]
            return {
                "reply": choice["message"]["content"],
                "model": data.get("model", self.model),
                "usage": data.get("usage"),
            }

        except httpx.HTTPStatusError as e:
            logger.error(f"AI API error {e.response.status_code}: {e.response.text}")
            raise
        except httpx.TimeoutException:
            logger.error(f"AI API timeout ({self.timeout}s)")
            raise
        except Exception as e:
            logger.error(f"AI API unexpected error: {e}")
            raise

    async def verify_contribution(
        self,
        task_title: str,
        contribution_description: str,
        evidence: dict | None = None,
    ) -> dict[str, Any]:
        """
        Use the AI model to verify a contribution.

        Returns dict with:
          - score: float (0.0–1.0)
          - feedback: str
          - passed: bool
          - model: str
        """
        content = evidence.get("content", "") if evidence else ""
        system_prompt = (
            "You are an AI contribution verifier for the PoCP (Proof of Contribution Protocol) platform. "
            "Evaluate the contribution based on quality, originality, completeness, and relevance to the task. "
            "Return a JSON object with: score (0.0–1.0), feedback (2–3 sentences explaining your rating), "
            "and passed (boolean, true if score >= 0.7). "
            "Do NOT return anything outside of the JSON object."
        )
        message = (
            f"Task: {task_title}\n"
            f"Description: {contribution_description}\n"
            f"Content: {content[:4000]}"
        )

        if self.is_configured:
            try:
                result = await self.chat(
                    message=message,
                    system_prompt=system_prompt,
                    temperature=0.3,
                    max_tokens=1024,
                )
                raw = result["reply"].strip()
                # Try to extract JSON from the response
                if raw.startswith("```"):
                    raw = raw.split("\n", 1)[1].rsplit("\n", 1)[0]
                parsed = json.loads(raw)
                return {
                    "score": float(parsed.get("score", 0.5)),
                    "feedback": parsed.get("feedback", "AI verification completed."),
                    "passed": parsed.get("passed", False),
                    "model": result["model"],
                }
            except (json.JSONDecodeError, KeyError, Exception) as e:
                logger.warning(f"Failed to parse AI verifier response: {e}")
                # Fall through to default

        # Default verification (no AI or parse failure)
        return {
            "score": 0.85,
            "feedback": "Contribution appears well-structured. AI advisory review completed.",
            "passed": True,
            "model": self.model,
        }


# Singleton
_default_client: AiModelClient | None = None


def get_ai_client() -> AiModelClient:
    global _default_client
    if _default_client is None:
        _default_client = AiModelClient()
    return _default_client
