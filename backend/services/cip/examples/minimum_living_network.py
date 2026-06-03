from __future__ import annotations

from services.cip.capability.registry import CIPCapabilityRegistry
from services.cip.discovery.discovery import CIPDiscoveryService
from services.cip.economy.accounting import CIPAccountingService
from services.cip.events.event_log import CIPEventLog
from services.cip.invocation.ledger import CIPInvocationLedger
from services.cip.node.registry import CIPNodeRegistry
from services.cip.proof.proof import CIPProofService
from services.cip.reputation.reputation import CIPReputationService
from services.cip.settlement.settlement import CIPSettlementService
from services.cip.types import SettlementParticipantData, TokenAccountData
from services.cip.verification.verifier import CIPVerifierService


def run_minimum_living_network_demo() -> dict:
    """Run the CIP minimum living network in memory.

    This demo does not replace the existing AI Commons V0.2 loop.
    """

    agent_entity_id = "agent_001"
    skill_entity_id = "skill_code_review_001"
    verifier_entity_id = "verifier_ai_001"

    nodes = CIPNodeRegistry()
    capabilities = CIPCapabilityRegistry()
    discovery = CIPDiscoveryService(capabilities)
    invocations = CIPInvocationLedger()
    proofs = CIPProofService()
    verifier = CIPVerifierService()
    settlements = CIPSettlementService()
    accounting = CIPAccountingService()
    reputation = CIPReputationService()
    event_log = CIPEventLog()

    skill_node = nodes.register_node(
        entity_id=skill_entity_id,
        node_type="service",
        public_key="ed25519:example-public-key",
        base_url="https://skill.example.com",
    )
    event_log.append("NodeRegistered", skill_entity_id, skill_node.node_id, skill_node.node_id)

    capability = capabilities.publish(
        entity_id=skill_entity_id,
        node_id=skill_node.node_id,
        capability_type="code_review",
        name="Python Code Review",
        unit="skill_invocation",
        price={"AIC": 5},
    )
    event_log.append("CapabilityPublished", skill_entity_id, capability.capability_id, skill_node.node_id)

    discovered = discovery.discover("code_review")

    invocation = invocations.create(
        task_id="task_001",
        caller_entity_id=agent_entity_id,
        callee_entity_id=skill_entity_id,
        capability_id=capability.capability_id,
        input_hash="sha256:input",
        cost_unit="AIC",
        cost_amount=5,
    )
    invocation = invocations.complete(invocation.invocation_id, "sha256:output")
    event_log.append("InvocationCompleted", agent_entity_id, invocation.invocation_id)

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
    event_log.append("ProofSubmitted", skill_entity_id, proof.proof_id, skill_node.node_id)

    verification = verifier.ai_advisory_verify(proof, verifier_entity_id)
    event_log.append("VerificationCompleted", verifier_entity_id, verification.verification_id)

    settlement = settlements.create_settlement(
        task_id=invocation.task_id,
        invocation_id=invocation.invocation_id,
        verification=verification,
        participants=[
            SettlementParticipantData(
                entity_id=skill_entity_id,
                role="skill_provider",
                unit="AIC",
                amount=5,
                reason="Provided verified code review capability.",
            ),
            SettlementParticipantData(
                entity_id=agent_entity_id,
                role="executor",
                unit="CP",
                amount=3,
                reason="Executed invocation.",
            ),
            SettlementParticipantData(
                entity_id=verifier_entity_id,
                role="verifier",
                unit="CP",
                amount=1,
                reason="Verified proof.",
            ),
        ],
    )
    event_log.append("SettlementExecuted", skill_entity_id, settlement.settlement_id, skill_node.node_id)

    accounts: dict[str, TokenAccountData] = accounting.apply_settlement({}, settlement)
    skill_reputation = reputation.update_success(skill_entity_id, "code_review")
    event_log.append("ReputationUpdated", skill_entity_id, "code_review", skill_node.node_id)

    return {
        "skill_node": skill_node,
        "capability": capability,
        "discovered": discovered,
        "invocation": invocation,
        "proof": proof,
        "verification": verification,
        "settlement": settlement,
        "accounts": accounts,
        "skill_reputation": skill_reputation,
        "events": event_log.events,
    }


if __name__ == "__main__":
    result = run_minimum_living_network_demo()
    for key, value in result.items():
        print(f"{key}: {value}")
