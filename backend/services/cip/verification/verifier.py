from __future__ import annotations

import uuid

from services.cip.types import ProofData, VerificationData


class CIPVerifierService:
    """AI advisory verifier skeleton."""

    def ai_advisory_verify(self, proof: ProofData, verifier_entity_id: str) -> VerificationData:
        score = 0.85 if proof.input_hash and proof.output_hash else 0.55
        decision = "approved" if score >= 0.7 else "needs_review"

        return VerificationData(
            verification_id=f"verify_{uuid.uuid4().hex[:16]}",
            proof_id=proof.proof_id,
            verifier_entity_id=verifier_entity_id,
            verification_type="ai_advisory",
            score=score,
            decision=decision,
            reason="Reference AI advisory verification based on proof completeness.",
            status="completed",
        )
