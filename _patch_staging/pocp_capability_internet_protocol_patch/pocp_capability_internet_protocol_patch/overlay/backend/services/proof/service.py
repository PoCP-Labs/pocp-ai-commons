from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
import uuid

@dataclass
class Proof:
    proof_id: str
    entity_id: str
    proof_type: str
    invocation_id: str | None = None
    task_id: str | None = None
    node_id: str | None = None
    input_hash: str | None = None
    output_hash: str | None = None
    evidence_ref: str | None = None
    signature: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

class ProofService:
    def submit(self, entity_id: str, proof_type: str, invocation_id: str | None = None,
               task_id: str | None = None, node_id: str | None = None,
               input_hash: str | None = None, output_hash: str | None = None,
               evidence_ref: str | None = None, signature: str | None = None) -> Proof:
        if proof_type != "human_evidence" and not invocation_id:
            raise ValueError("Proof requires invocation_id unless proof_type is human_evidence")
        return Proof(f"proof_{uuid.uuid4().hex[:16]}", entity_id, proof_type, invocation_id,
                     task_id, node_id, input_hash, output_hash, evidence_ref, signature)
