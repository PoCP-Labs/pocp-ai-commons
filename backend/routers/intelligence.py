"""External Intelligence API — capability layer surface for third parties."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from intelligence import capability_layer
from intelligence.protocol import ENTITY_TYPES
from services.neural_network_registry import list_neural_sources, load_neural_network_sources
from services.finalization import finalization_policy_manifest
from services.rights_conversion import rights_rules_manifest
from services.compute_registry import compute_status_manifest
from services.oss_entity_registry import ensure_all_oss_entities, list_oss_entity_specs
from services.peer_compute import list_peer_compute_status, validate_peer_witness_request
from services.peer_trust import issue_peer_challenge, peer_trust_manifest
from services.peer_mcp import peer_mcp_enabled
from services.remote_mcp_invoke import run_remote_mcp_invoke
from services.remote_witness import run_witness
from services.a2a_agent_card import build_entity_agent_card, build_node_agent_card
from services.a2a_task_bridge import handle_jsonrpc_call
from services.entity_connections import entity_connection_matrix
from services.entity_dialogue import (
    ENTITY_DIALOGUE_SCHEMA,
    dialogue_manifest,
    route_dialogue,
)
from models.user_account import UserAccount
from routers.auth import require_current_user

router = APIRouter(prefix="/api/v1/intelligence", tags=["intelligence"])


class MatchRequest(BaseModel):
    task_id: str | None = None
    contribution_type: str | None = None
    limit: int = Field(default=5, ge=1, le=20)


class DedupCheckRequest(BaseModel):
    description: str | None = None
    evidence: dict | None = None
    exclude_contribution_id: str | None = None


class WitnessRequest(BaseModel):
    context: dict
    provider: str = Field(default="mock", description="mock, simulated, openai, deepseek, …")
    source_node_id: str | None = None


class ComputeInferenceRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=32000)
    provider: str = Field(default="mock")
    model: str | None = None
    system_content: str | None = None
    source_node_id: str | None = None


class PeerMcpInvokeRequest(BaseModel):
    portable_id: str = Field(min_length=3, description="MCP tool portable_id, e.g. mcp:demo-fetch/fetch")
    arguments: dict = Field(default_factory=dict)
    invoke_mode: str | None = Field(default="live", description="live or stub")
    source_node_id: str | None = None


class EntityRegisterRequest(BaseModel):
    entity_type: str = Field(description="tool, dataset, workflow, agent, skill, organization, etc.")
    name: str
    description: str | None = None
    tags: list[str] = Field(default_factory=list)
    capabilities: list[str] = Field(default_factory=list)


class ComputeRegisterRequest(BaseModel):
    offers: list[dict[str, Any]] = Field(min_length=1)
    endpoints: dict[str, Any] = Field(default_factory=dict)
    capacity: dict[str, Any] = Field(default_factory=dict)
    policy: dict[str, Any] = Field(default_factory=dict)
    accountability: dict[str, Any] = Field(default_factory=dict)
    status: str = "active"


class FederationIngestRequest(BaseModel):
    packet: dict


class StudyAgentRunRequest(BaseModel):
    topic: str = Field(min_length=3, max_length=2000)
    task_id: str | None = None
    agent_entity_id: str | None = None
    skill_entity_id: str | None = None
    llm_entity_id: str | None = None
    llm_provider: str | None = Field(default=None, description="mock, openai, ollama, …")
    contribution_id: str | None = None
    submit_contribution: bool = Field(
        default=False,
        description="When true, create a submitted Contribution Event from the StudyAgent draft",
    )


@router.get("/protocol/stack")
def intelligence_protocol_stack():
    """Protocol / Capability / Transaction layer map — where PoCP should be built."""
    return capability_layer.protocol_stack()


@router.get("/protocol")
def intelligence_protocol():
    """Unified contribution protocol descriptor — everything connects through contribution."""
    return capability_layer.protocol()


@router.get("/status")
def intelligence_status():
    """Capability module registry and readiness."""
    return capability_layer.status()


@router.get("/finalization/policy")
def finalization_policy():
    """Active witness-quorum / auto-finalization policy for this instance."""
    return finalization_policy_manifest()


@router.get("/protocol/rights-rules")
def protocol_rights_rules():
    """Versioned contribution-to-rights rules (pocp.rights_rules.v0.1)."""
    return rights_rules_manifest()


@router.get("/protocol/primitives")
def protocol_primitives():
    """Protocol-layer primitive schemas exposed by this node."""
    from services.capability_receipt import CAPABILITY_RECEIPT_SCHEMA
    from services.rights_conversion import CONVERSION_SCHEMA, RIGHTS_RULES_SCHEMA

    from intelligence.entity_ontology import ENTITY_CONNECTION_SCHEMA, connection_matrix_document
    from services.entity_dialogue import ENTITY_DIALOGUE_SCHEMA, ENTITY_DIALOGUE_RESPONSE_SCHEMA
    from services.trust_policy_bundle import TRUST_POLICY_BUNDLE_SCHEMA, trust_policy_bundle_manifest

    return {
        "rights_rules_schema": RIGHTS_RULES_SCHEMA,
        "contribution_to_rights_conversion_schema": CONVERSION_SCHEMA,
        "capability_receipt_schema": CAPABILITY_RECEIPT_SCHEMA,
        "entity_connection_schema": ENTITY_CONNECTION_SCHEMA,
        "entity_dialogue_schema": ENTITY_DIALOGUE_SCHEMA,
        "entity_dialogue_response_schema": ENTITY_DIALOGUE_RESPONSE_SCHEMA,
        "trust_policy_bundle_schema": TRUST_POLICY_BUNDLE_SCHEMA,
        "entity_connections": connection_matrix_document(),
        "trust_policy_bundle": trust_policy_bundle_manifest(),
        "finalization_policy": finalization_policy_manifest(),
        "rights_rules": rights_rules_manifest(),
    }


@router.get("/protocol/entity-connections")
def protocol_entity_connections():
    """Entity type connection matrix — how each entity type links in the protocol."""
    return entity_connection_matrix()


@router.get("/protocol/trust-policy-bundle")
def protocol_trust_policy_bundle():
    """Trust + finalization + import rules bundle for federation peers."""
    from services.trust_policy_bundle import trust_policy_bundle_manifest

    return trust_policy_bundle_manifest()


@router.get("/protocol/entity-dialogue")
def protocol_entity_dialogue():
    """Entity Dialogue Protocol manifest — L2 native envelope for Entity communication."""
    return dialogue_manifest()


class EntityDialogueIn(BaseModel):
    schema: str = Field(alias="schema")
    dialogue_id: str
    kind: str
    from_: dict = Field(alias="from")
    to: dict
    payload: dict = Field(default_factory=dict)
    refs: dict = Field(default_factory=dict)
    crypto: dict | None = None

    model_config = {"populate_by_name": True}


@router.post("/dialogue")
def node_dialogue(
    body: EntityDialogueIn,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(require_current_user),
):
    """Route pocp.entity_dialogue.v0.1 envelope on this node (native Entity dialogue entry)."""
    if body.schema != ENTITY_DIALOGUE_SCHEMA:
        raise HTTPException(status_code=400, detail=f"schema must be {ENTITY_DIALOGUE_SCHEMA}")
    envelope = body.model_dump(by_alias=True)
    if not envelope.get("from", {}).get("entity_id"):
        envelope["from"] = {**envelope["from"], "entity_id": current_user.entity_id}
    response = route_dialogue(db, envelope)
    db.commit()
    return response


@router.post("/entities/{entity_id}/dialogue")
def entity_dialogue(
    entity_id: str,
    body: EntityDialogueIn,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(require_current_user),
):
    """Route dialogue envelope targeted at a specific Entity."""
    if body.schema != ENTITY_DIALOGUE_SCHEMA:
        raise HTTPException(status_code=400, detail=f"schema must be {ENTITY_DIALOGUE_SCHEMA}")
    envelope = body.model_dump(by_alias=True)
    if not envelope.get("from", {}).get("entity_id"):
        envelope["from"] = {**envelope["from"], "entity_id": current_user.entity_id}
    response = route_dialogue(db, envelope, expected_target_entity_id=entity_id)
    db.commit()
    return response


@router.get("/compute/status")
def compute_status():
    """Distributed compute adapters active on this node (witness, embeddings, agents)."""
    return compute_status_manifest()


@router.get("/oss-entities")
def oss_entities(db: Session = Depends(get_db)):
    """Open-source project entities from neural_network + oss_community registries."""
    from models.entity import Entity

    specs = list_oss_entity_specs()
    ids = [s["entity_id"] for s in specs if s.get("entity_id")]
    existing = {e.id: e for e in db.query(Entity).filter(Entity.id.in_(ids)).all()} if ids else {}
    return {
        "spec_version": "0.1",
        "entity_count": len(specs),
        "persisted_count": len(existing),
        "entities": [
            {
                **spec,
                "persisted": spec.get("entity_id") in existing,
                "entity_status": existing[spec["entity_id"]].status.value
                if spec.get("entity_id") in existing
                else None,
            }
            for spec in specs
        ],
        "docs": "docs/OSS-ENTITY-REGISTRY.md",
    }


@router.post("/oss-entities/sync")
def oss_entities_sync(db: Session = Depends(get_db)):
    """Refresh Entity rows from OSS YAML registries (startup also runs this)."""
    summary = ensure_all_oss_entities(db)
    db.commit()
    return {"sync_summary": summary, "entities": list_oss_entity_specs()}


@router.get("/compute/peers")
def compute_peers():
    """Probe trusted peer compute nodes (NN-5 federated inference routing)."""
    return list_peer_compute_status()


@router.get("/compute/peer/trust")
def compute_peer_trust():
    """Peer handshake manifest — algorithms, headers, challenge endpoint (BI-2)."""
    return peer_trust_manifest()


@router.get("/compute/peer/challenge")
def compute_peer_challenge(node_id: str | None = Query(default=None)):
    """Issue one-time handshake nonce for challenge-response peer auth."""
    return issue_peer_challenge(node_id=node_id)


@router.post("/compute/witness")
async def compute_witness(body: WitnessRequest, request: Request):
    """Run one witness provider — callable by trusted peer nodes for federated verify."""
    headers = {k.lower(): v for k, v in request.headers.items()}
    if not validate_peer_witness_request(headers):
        raise HTTPException(
            status_code=403,
            detail=(
                "Peer witness denied. Configure POCP_PEER_COMPUTE_SECRET handshake, "
                "Ed25519 trusted node key, POCP_ALLOW_PEER_WITNESS dev bypass, or legacy X-POCP-Peer-Secret."
            ),
        )
    result = await run_witness(body.context, provider=body.provider)
    return {
        "node_id": compute_status_manifest().get("node_id"),
        "source_node_id": body.source_node_id,
        "provider_requested": body.provider,
        "result": result.model_dump(),
    }


@router.post("/compute/inference")
async def compute_inference(body: ComputeInferenceRequest, request: Request):
    """Run llm_inference on this node — callable by trusted peers (NN-5 remote routing)."""
    from services.ai_chat import generate_ai_reply

    headers = {k.lower(): v for k, v in request.headers.items()}
    if not validate_peer_witness_request(headers):
        raise HTTPException(
            status_code=403,
            detail=(
                "Peer inference denied. Configure POCP_PEER_COMPUTE_SECRET handshake, "
                "Ed25519 trusted node key, or dev bypass POCP_ALLOW_PEER_WITNESS."
            ),
        )
    output, provider, model = await generate_ai_reply(
        body.prompt,
        provider=body.provider,
        model=body.model,
        system_content=body.system_content,
    )
    return {
        "node_id": compute_status_manifest().get("node_id"),
        "source_node_id": body.source_node_id,
        "provider": provider,
        "model": model,
        "output": output,
        "capability": "llm_inference",
    }


@router.post("/compute/mcp/invoke")
async def compute_mcp_invoke(
    body: PeerMcpInvokeRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Execute MCP tool by portable_id — callable by trusted peers for federated MCP routing."""
    headers = {k.lower(): v for k, v in request.headers.items()}
    if not validate_peer_witness_request(headers):
        raise HTTPException(
            status_code=403,
            detail=(
                "Peer MCP denied. Configure POCP_PEER_COMPUTE_SECRET handshake, "
                "Ed25519 trusted node key, or dev bypass POCP_ALLOW_PEER_WITNESS."
            ),
        )
    result = await run_remote_mcp_invoke(
        db,
        portable_id=body.portable_id,
        arguments=body.arguments,
        invoke_mode=body.invoke_mode,
    )
    return {
        "node_id": compute_status_manifest().get("node_id"),
        "source_node_id": body.source_node_id,
        "peer_mcp_enabled": peer_mcp_enabled(),
        **result,
    }


@router.get("/graph/analytics")
def graph_analytics(
    review_limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Advisory graph analytics — review queue priority & centrality (NN-4 lite)."""
    return capability_layer.graph_analytics(db, review_limit=review_limit)


@router.post("/dedup/check")
def semantic_dedup_check(
    body: DedupCheckRequest,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(require_current_user),
):
    """Advisory semantic duplicate hints before submit (sentence-transformers / Ollama)."""
    return capability_layer.dedup_check(
        db,
        entity_id=current_user.entity_id,
        description=body.description,
        evidence=body.evidence,
        exclude_contribution_id=body.exclude_contribution_id,
    )


@router.get("/agent-card")
def node_agent_card(db: Session = Depends(get_db)):
    """A2A Agent Card for this PoCP node — mirrors /.well-known/agent.json."""
    return build_node_agent_card(db)


@router.get("/entities/{entity_id}/agent-card")
def entity_agent_card(entity_id: str, db: Session = Depends(get_db)):
    """A2A Agent Card for a PoCP Entity (ComputeProfile + declared capabilities)."""
    card = build_entity_agent_card(db, entity_id)
    if card is None:
        raise HTTPException(status_code=404, detail="Entity not found")
    return card


@router.get("/entities/{entity_id}/a2a")
def entity_a2a_surface(entity_id: str, db: Session = Depends(get_db)):
    """A2A service descriptor — Agent Card + JSON-RPC task bridge."""
    card = build_entity_agent_card(db, entity_id)
    if card is None:
        raise HTTPException(status_code=404, detail="Entity not found")
    return {
        "protocol": "a2a",
        "protocol_version": card["pocp"]["a2a_protocol_version"],
        "agent_card": card,
        "jsonrpc_endpoint": f"/api/v1/intelligence/entities/{entity_id}/a2a",
        "methods": ["SendMessage", "GetTask", "ListTasks", "GetAgentCard"],
        "task_bridge": {
            "contribution_bound": True,
            "auto_finalization_enabled": True,
            "send_message_maps_to": "ContributionEvent",
            "auto_verify": f"/api/v1/contributions/{{contribution_id}}/auto-verify",
        },
    }


@router.post("/entities/{entity_id}/a2a")
async def entity_a2a_jsonrpc(
    entity_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(require_current_user),
):
    """A2A JSON-RPC 2.0 — SendMessage creates Contribution bound to target Entity."""
    card = build_entity_agent_card(db, entity_id)
    if card is None:
        raise HTTPException(status_code=404, detail="Entity not found")
    payload = await request.json()
    if isinstance(payload, list):
        raise HTTPException(status_code=400, detail="JSON-RPC batch not supported in v0.1")
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="JSON-RPC body must be an object")
    return handle_jsonrpc_call(db, user=current_user, payload=payload, target_entity_id=entity_id)


@router.get("/a2a")
def node_a2a_surface(db: Session = Depends(get_db)):
    """Node-level A2A service descriptor."""
    card = build_node_agent_card(db)
    return {
        "protocol": "a2a",
        "protocol_version": card["pocp"]["a2a_protocol_version"],
        "agent_card": card,
        "jsonrpc_endpoint": "/api/v1/intelligence/a2a",
        "methods": ["SendMessage", "GetTask", "ListTasks", "GetAgentCard"],
        "entity_cards": "/api/v1/intelligence/entities/{entity_id}/agent-card",
        "well_known": "/.well-known/agent.json",
        "task_bridge": {
            "contribution_bound": True,
            "auto_finalization_enabled": True,
            "send_message_maps_to": "ContributionEvent",
        },
    }


@router.post("/a2a")
async def node_a2a_jsonrpc(
    request: Request,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(require_current_user),
):
    """Node-level A2A JSON-RPC 2.0 — SendMessage → Contribution (optional targetEntityId in metadata)."""
    payload = await request.json()
    if isinstance(payload, list):
        raise HTTPException(status_code=400, detail="JSON-RPC batch not supported in v0.1")
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="JSON-RPC body must be an object")
    return handle_jsonrpc_call(db, user=current_user, payload=payload, target_entity_id=None)


@router.get("/entities/{entity_id}/profile")
def entity_intelligence_profile(entity_id: str, db: Session = Depends(get_db)):
    """Unified entity view: wallet, reputation, contribution touchpoints."""
    profile = capability_layer.entity_profile(db, entity_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Entity not found")
    return profile


@router.post("/entities/register", status_code=201)
def register_contribution_entity(
    body: EntityRegisterRequest,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(require_current_user),
):
    """Register any contribution-capable entity type through the capability layer."""
    if body.entity_type not in ENTITY_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"entity_type must be one of: {', '.join(ENTITY_TYPES)}",
        )
    try:
        entity = capability_layer.register_entity(
            db,
            entity_type=body.entity_type,
            name=body.name,
            description=body.description,
            tags=body.tags,
            capabilities=body.capabilities,
            owner_id=current_user.entity_id,
            creator_id=current_user.entity_id,
        )
        db.commit()
        db.refresh(entity)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "entity": {
            "id": entity.id,
            "entity_type": entity.entity_type.value,
            "name": entity.name,
            "description": entity.description,
            "metadata": entity.metadata_ or {},
        },
        "contribution_capable": True,
        "principle": capability_layer.principle,
    }


@router.post("/entities/{entity_id}/compute/register")
def register_entity_compute_profile(
    entity_id: str,
    body: ComputeRegisterRequest,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(require_current_user),
):
    """Register ComputeProfile on Entity — distributed intelligence provider mesh."""
    entity = capability_layer.register_compute_profile(
        db,
        entity_id=entity_id,
        profile=body.model_dump(),
        owner_entity_id=current_user.entity_id,
    )
    db.commit()
    db.refresh(entity)
    return {
        "entity_id": entity.id,
        "compute_profile": (entity.metadata_ or {}).get("compute_profile"),
        "principle": capability_layer.principle,
    }


@router.get("/contributions/{contribution_id}/packet")
def contribution_intelligence_packet(
    contribution_id: str,
    db: Session = Depends(get_db),
    _user=Depends(require_current_user),
):
    """Full advisory intelligence packet for a contribution (verification, rewards, Clarion)."""
    packet = capability_layer.intelligence_packet(db, contribution_id)
    if not packet:
        raise HTTPException(status_code=404, detail="Contribution not found")
    return packet


@router.get("/federation/export/{contribution_id}")
def federation_intelligence_export(
    contribution_id: str,
    db: Session = Depends(get_db),
    _user=Depends(require_current_user),
):
    """Cross-node intelligence + proof bundle for federation peers."""
    packet = capability_layer.federation_export(db, contribution_id)
    if not packet:
        raise HTTPException(status_code=404, detail="Contribution not found")
    return packet


@router.post("/federation/ingest-preview")
def federation_intelligence_ingest_preview(body: FederationIngestRequest):
    """Advisory summary of a received federation intelligence packet (no import)."""
    return capability_layer.federation_ingest_summary(body.packet)


@router.get("/governance/summary")
def governance_summary(db: Session = Depends(get_db)):
    """Advisory governance snapshot — network health, queues, policy parameters."""
    return capability_layer.governance_summary(db)


@router.post("/match")
def match_capabilities(
    body: MatchRequest,
    db: Session = Depends(get_db),
    _user=Depends(require_current_user),
):
    """Recommend agents and skills (advisory matching engine v0.3)."""
    return capability_layer.match_capabilities(
        db,
        task_id=body.task_id,
        contribution_type=body.contribution_type,
        limit=body.limit,
    )


@router.get("/neural-sources")
def neural_network_sources(
    status: str | None = None,
    category: str | None = None,
):
    """GitHub neural-network / agent technology registry (see docs/NEURAL-NETWORK-GITHUB-ADOPTION.md)."""
    registry = load_neural_network_sources()
    return {
        "spec_version": registry.get("spec_version", "0.1"),
        "adoption_policy": registry.get("adoption_policy", {}),
        "categories": registry.get("categories", {}),
        "sources": list_neural_sources(status=status, category=category),
        "declined": registry.get("declined", {}),
        "docs": "docs/NEURAL-NETWORK-GITHUB-ADOPTION.md",
    }


@router.post("/agents/study/run")
async def run_study_agent(
    body: StudyAgentRunRequest,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(require_current_user),
):
    """StudyAgent multi-step run → InvocationTrace (capability layer agent_runtime)."""
    result = await capability_layer.run_study_agent(
        db,
        human_entity_id=current_user.entity_id,
        topic=body.topic,
        task_id=body.task_id,
        agent_entity_id=body.agent_entity_id,
        skill_entity_id=body.skill_entity_id,
        llm_entity_id=body.llm_entity_id,
        llm_provider=body.llm_provider,
        contribution_id=body.contribution_id,
        submit_contribution=body.submit_contribution,
    )
    db.commit()
    return result
