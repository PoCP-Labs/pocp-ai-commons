from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

@dataclass
class GraphEdge:
    source_id: str
    target_id: str
    edge_type: str
    metadata: dict[str, Any] = field(default_factory=dict)

class ReputationGraphService:
    def closed_loop_edges(self, entity_id: str, node_id: str, capability_id: str,
                          invocation_id: str, proof_id: str, verification_id: str,
                          settlement_id: str, reputation_id: str) -> list[GraphEdge]:
        return [
            GraphEdge(entity_id, node_id, "owns_node"),
            GraphEdge(node_id, capability_id, "provides_capability"),
            GraphEdge(capability_id, invocation_id, "invoked_as"),
            GraphEdge(invocation_id, proof_id, "produces_proof"),
            GraphEdge(proof_id, verification_id, "verified_by"),
            GraphEdge(verification_id, settlement_id, "settles"),
            GraphEdge(settlement_id, reputation_id, "updates_reputation"),
        ]
