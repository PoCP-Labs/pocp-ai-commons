"""HTTP callback verifier adapter for external review services."""

import os

import httpx

from services.verifiers.base import BaseVerifier, VerifierResult
from services.verifiers.openai_verifier import normalize_result


class HttpVerifier(BaseVerifier):
    """POST context to an external verifier endpoint; expect VerifierResult JSON."""

    def __init__(
        self,
        name: str,
        url: str,
        api_key: str | None = None,
        timeout: int = 60,
    ):
        self.provider_name = name
        self.url = url.rstrip("/")
        self.api_key = api_key or os.getenv(f"POCP_VERIFIER_{name.upper()}_API_KEY", "")
        self.timeout = timeout

    @property
    def available(self) -> bool:
        return bool(self.url)

    async def verify(self, context: dict) -> VerifierResult:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                self.url,
                headers=headers,
                json={"context": context, "provider": self.provider_name},
            )
            resp.raise_for_status()
            data = resp.json()

        if "provider" in data and "quality" in data:
            return VerifierResult.model_validate(data)
        return normalize_result(
            self.provider_name,
            str(data.get("model") or "external"),
            data,
        )
