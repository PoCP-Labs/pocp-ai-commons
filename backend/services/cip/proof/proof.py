from __future__ import annotations

import uuid

from services.cip.types import ProofData


class CIPProofService:
    """In-memory proof service."""

    def __init__(self) -> None:
        self.proofs: dict[str, ProofData] = {}

    def submit(
        self,
        entity_id: str,
        proof_type: str,
        invocation_id: str | None = None,
        node_id: str | None = None,
        task_id: str | None = None,
        input_hash: str | None = None,
        output_hash: str | None = None,
        evidence_ref: str | None = None,
        signature: str | None = None,
    ) -> ProofData:
        if proof_type != "human_evidence" and not invocation_id:
            raise ValueError("Proof requires invocation_id unless proof_type is human_evidence.")

        proof = ProofData(
            proof_id=f"proof_{uuid.uuid4().hex[:16]}",
            entity_id=entity_id,
            proof_type=proof_type,
            invocation_id=invocation_id,
            node_id=node_id,
            task_id=task_id,
            input_hash=input_hash,
            output_hash=output_hash,
            evidence_ref=evidence_ref,
            signature=signature,
        )
        self.proofs[proof.proof_id] = proof
        return proof
