"""Genesis witness nodes as named verifier adapters (Lumen-0, DeSui)."""

from services.verifiers.base import BaseVerifier, VerifierResult


class WitnessVerifier(BaseVerifier):
    """Wrap an inner verifier with a genesis witness identity."""

    def __init__(self, provider_slug: str, display_name: str, inner: BaseVerifier):
        self.provider_name = provider_slug
        self.display_name = display_name
        self.inner = inner

    @property
    def available(self) -> bool:
        return getattr(self.inner, "available", True)

    async def verify(self, context: dict) -> VerifierResult:
        result = await self.inner.verify(context)
        prefix = f"[{self.display_name} witness]"
        rationale = result.rationale if result.rationale.startswith(prefix) else f"{prefix} {result.rationale}"
        return result.model_copy(
            update={
                "provider": self.provider_name,
                "model": f"{self.display_name.lower()}-witness",
                "rationale": rationale,
            }
        )
