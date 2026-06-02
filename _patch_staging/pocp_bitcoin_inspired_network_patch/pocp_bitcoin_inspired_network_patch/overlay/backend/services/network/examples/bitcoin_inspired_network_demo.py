from __future__ import annotations
from backend.services.network.confirmation import ConfirmationService
from backend.services.network.event_batch import EventBatchService
from backend.services.network.mempool import PoCPMempool
from backend.services.network.peer import PeerRegistry
from backend.services.network.types import ProtocolEvent

def run_bitcoin_inspired_network_demo() -> dict:
    peers = PeerRegistry()
    mempool = PoCPMempool()
    batcher = EventBatchService()
    confirmations = ConfirmationService()

    agent = peers.add_peer("node_agent_001", "agent_001", ["agent_node", "light_node"])
    skill = peers.add_peer("node_skill_001", "skill_001", ["skill_node", "service_node"])
    verifier = peers.add_peer("node_verifier_001", "verifier_001", ["verifier_node"])
    indexer = peers.add_peer("node_indexer_001", "indexer_001", ["indexer_node", "full_event_node"])

    invocation = ProtocolEvent.create("InvocationCreated", {
        "caller_entity_id": agent.entity_id,
        "callee_entity_id": skill.entity_id,
        "capability_id": "cap_code_review",
        "input_hash": "sha256:input",
    }, entity_id=agent.entity_id, node_id=agent.node_id)

    proof = ProtocolEvent.create("ProofSubmitted", {
        "invocation_event_id": invocation.event_id,
        "proof_type": "skill_invocation_result",
        "output_hash": "sha256:output",
    }, entity_id=skill.entity_id, node_id=skill.node_id, previous_event_hash=invocation.event_hash())

    verification = ProtocolEvent.create("VerificationCompleted", {
        "proof_event_id": proof.event_id,
        "decision": "approved",
        "score": 0.86,
    }, entity_id=verifier.entity_id, node_id=verifier.node_id, previous_event_hash=proof.event_hash())

    settlement = ProtocolEvent.create("SettlementExecuted", {
        "verification_event_id": verification.event_id,
        "participants": [
            {"entity_id": skill.entity_id, "unit": "AIC", "amount": 5},
            {"entity_id": verifier.entity_id, "unit": "CP", "amount": 2},
        ],
    }, entity_id=skill.entity_id, node_id=skill.node_id, previous_event_hash=verification.event_hash())

    for event in [invocation, proof, verification, settlement]:
        mempool.add(event)

    events = mempool.drain()
    batch = batcher.create_batch(events, created_by_node_id=indexer.node_id)
    confirmation_status = confirmations.status_for_event(settlement, level=5)

    return {
        "peers": peers.all_peers(),
        "events": events,
        "batch": batch,
        "merkle_root": batch.event_merkle_root,
        "confirmation": confirmation_status,
    }
