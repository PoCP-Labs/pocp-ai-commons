from __future__ import annotations
from backend.services.cip.types import GraphEdgeData, ReputationData

class CIPReputationGraph:
    def update_success(self, entity_id: str, scope: str, current: ReputationData | None = None) -> ReputationData:
        if current is None:
            current = ReputationData(entity_id=entity_id, scope=scope)
        current.success_count += 1
        total = current.success_count + current.failure_count + current.dispute_count
        current.score = current.success_count / total if total else 0.0
        return current

    def chain_edges(self, entity_id: str, node_id: str, capability_id: str, invocation_id: str, proof_id: str, verification_id: str, settlement_id: str) -> list[GraphEdgeData]:
        return [
            GraphEdgeData(entity_id, node_id, "owns_node"),
            GraphEdgeData(node_id, capability_id, "publishes_capability"),
            GraphEdgeData(capability_id, invocation_id, "invoked_as"),
            GraphEdgeData(invocation_id, proof_id, "submits_proof"),
            GraphEdgeData(proof_id, verification_id, "verified_by"),
            GraphEdgeData(verification_id, settlement_id, "settles"),
        ]
