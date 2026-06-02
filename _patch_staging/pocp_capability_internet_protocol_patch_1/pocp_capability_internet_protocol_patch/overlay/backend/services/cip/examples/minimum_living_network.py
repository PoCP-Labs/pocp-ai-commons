from __future__ import annotations

from backend.services.cip.capability.registry import CIPCapabilityRegistry
from backend.services.cip.discovery.discovery import CIPDiscoveryService
from backend.services.cip.economy.accounting import CIPAccountingService
from backend.services.cip.identity.signature import CIPSignatureService
from backend.services.cip.invocation.ledger import CIPInvocationLedger
from backend.services.cip.node.heartbeat import CIPHeartbeatService
from backend.services.cip.node.registry import CIPNodeRegistry
from backend.services.cip.p2p.events import CIPEventLog
from backend.services.cip.proof.proof import CIPProofService
from backend.services.cip.reputation.graph import CIPReputationGraph
from backend.services.cip.settlement.settlement import CIPSettlementService
from backend.services.cip.types import SettlementParticipantData, TokenAccountData
from backend.services.cip.verification.verifier import CIPVerifierService


def run_minimum_living_network_demo() -> dict:
    signature = CIPSignatureService()
    event_log = CIPEventLog()
    node_registry = CIPNodeRegistry()
    heartbeat = CIPHeartbeatService()
    capabilities = CIPCapabilityRegistry()
    discovery = CIPDiscoveryService(capabilities)
    invocations = CIPInvocationLedger()
    proofs = CIPProofService()
    verifier = CIPVerifierService()
    settlement_service = CIPSettlementService()
    accounting = CIPAccountingService()
    reputation_graph = CIPReputationGraph()

    agent_entity_id = "agent_001"
    skill_entity_id = "skill_code_review_001"
    verifier_entity_id = "verifier_ai_001"

    skill_node = node_registry.register_node(
        entity_id=skill_entity_id,
        node_type="service",
        public_key="ed25519:example-skill-public-key",
        base_url="https://skill.example.com",
    )
    heartbeat.mark_active(skill_node)

    capability = capabilities.publish(
        entity_id=skill_entity_id,
        node_id=skill_node.node_id,
        capability_type="code_review",
        name="Python Code Review",
        unit="skill_invocation",
        price={"AIC": 5},
    )

    discovered = discovery.discover_capabilities("code_review")

    invocation = invocations.create(
        task_id="task_001",
        caller_entity_id=agent_entity_id,
        callee_entity_id=skill_entity_id,
        capability_id=capability.capability_id,
        input_hash="sha256:input",
        cost_unit="AIC",
        cost_amount=5,
    )
    invocation = invocations.complete(invocation.invocation_id, output_hash="sha256:output")

    proof = proofs.submit(
        entity_id=skill_entity_id,
        node_id=skill_node.node_id,
        proof_type="skill_invocation_result",
        task_id=invocation.task_id,
        invocation_id=invocation.invocation_id,
        input_hash=invocation.input_hash,
        output_hash=invocation.output_hash,
        evidence_ref="ipfs://example-proof-cid",
        signature="sig_example",
    )

    verification = verifier.ai_advisory_verify(proof=proof, verifier_entity_id=verifier_entity_id)

    settlement = settlement_service.create_settlement(
        task_id=invocation.task_id,
        invocation_id=invocation.invocation_id,
        verification=verification,
        participants=[
            SettlementParticipantData(skill_entity_id, "skill_provider", "AIC", 5, "Provided verified code review capability."),
            SettlementParticipantData(agent_entity_id, "executor", "CP", 3, "Executed task routing and invocation."),
            SettlementParticipantData(verifier_entity_id, "verifier", "CP", 1, "Verified proof."),
        ],
    )

    accounts: dict[str, TokenAccountData] = accounting.apply_settlement({}, settlement)
    reputation = reputation_graph.update_success(skill_entity_id, "code_review")
    graph_edges = reputation_graph.chain_edges(
        skill_entity_id, skill_node.node_id, capability.capability_id, invocation.invocation_id,
        proof.proof_id, verification.verification_id, settlement.settlement_id
    )

    for event_type, entity_id, payload in [
        ("NodeRegistered", skill_entity_id, skill_node.node_id),
        ("CapabilityPublished", skill_entity_id, capability.capability_id),
        ("InvocationCreated", agent_entity_id, invocation.invocation_id),
        ("ProofSubmitted", skill_entity_id, proof.proof_id),
        ("VerificationCompleted", verifier_entity_id, verification.verification_id),
        ("SettlementExecuted", skill_entity_id, settlement.settlement_id),
        ("ReputationUpdated", skill_entity_id, reputation.scope),
    ]:
        event_log.append(signature.create_event(event_type, entity_id, payload, skill_node.node_id if entity_id == skill_entity_id else None))

    return {
        "skill_node": skill_node,
        "capability": capability,
        "discovered": discovered,
        "invocation": invocation,
        "proof": proof,
        "verification": verification,
        "settlement": settlement,
        "accounts": accounts,
        "reputation": reputation,
        "graph_edges": graph_edges,
        "events": event_log.events,
    }


if __name__ == "__main__":
    result = run_minimum_living_network_demo()
    for key, value in result.items():
        print(f"{key}: {value}")
