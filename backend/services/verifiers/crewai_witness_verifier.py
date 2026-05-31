"""Multi-agent CrewAI witness adapter for MultiVerifier consensus."""

from __future__ import annotations

from services.crewai_witness import crewai_witness_enabled, run_crewai_witness
from services.verifiers.base import BaseVerifier, VerifierResult


class CrewaiWitnessVerifier(BaseVerifier):
    """Role-based witness crew — native sequential roles, optional CrewAI library, or HTTP gateway."""

    provider_name = "crewai"

    @property
    def available(self) -> bool:
        return crewai_witness_enabled()

    async def verify(self, context: dict) -> VerifierResult:
        if not self.available:
            raise RuntimeError("ENABLE_CREWAI_WITNESS is not true")
        return await run_crewai_witness(context)
