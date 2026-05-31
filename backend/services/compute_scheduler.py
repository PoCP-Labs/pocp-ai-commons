"""Distributed compute scheduler — Entity profiles + local node + peer overlay (v0.1)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from models.entity import Entity, EntityStatus
from services.compute_profile import entity_offers_capability, get_compute_profile, list_compute_provider_entities
from services.compute_receipt import build_compute_receipt
from services.compute_reputation import load_compute_provider_reputation_map
from services.compute_registry import compute_status_manifest, load_compute_registry
from services.peer_compute import PeerComputeNode, load_peer_compute_nodes, select_peer_compute_node
from services.protocol_config import get_rewards_config


@dataclass
class ComputeJob:
    capability: str
    initiator_entity_id: str | None = None
    contribution_id: str | None = None
    task_id: str | None = None
    constraints: dict[str, Any] = field(default_factory=dict)


@dataclass
class ComputeProviderCandidate:
    source: str  # local_node | entity | peer_node
    provider_entity_id: str | None
    provider_node_id: str | None
    base_url: str | None
    trust_weight: float
    adapter: str | None = None
    model: str | None = None
    region: str | None = None
    rank_score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


def _local_node_candidate(job: ComputeJob) -> ComputeProviderCandidate | None:
    manifest = compute_status_manifest()
    adapters = manifest.get("active_adapters") or []
    registry = load_compute_registry()
    local = registry.get("local_node") or {}
    roles = set(local.get("roles") or [])

    capability_map = {
        "llm_inference": "inference",
        "embeddings": "embeddings",
        "witness": "witness",
        "mcp_host": "mcp",
        "agent_runtime": "agent_runtime",
    }
    needed_role = capability_map.get(job.capability)
    if needed_role and needed_role not in roles and job.capability not in ("witness", "llm_inference"):
        if not adapters:
            return None

    if job.capability == "witness" and not adapters and "mock" not in adapters:
        pass  # witness may still run via mock verifier locally

    backend_url = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")
    return ComputeProviderCandidate(
        source="local_node",
        provider_entity_id=local.get("provider_entity_id"),
        provider_node_id=manifest.get("node_id"),
        base_url=backend_url,
        trust_weight=1.0,
        adapter=adapters[0] if adapters else "local",
        region=str(local.get("region") or ""),
        rank_score=0.0,
        metadata={"active_adapters": adapters},
    )


def _entity_candidates(db: Session, job: ComputeJob, initiator: Entity | None) -> list[ComputeProviderCandidate]:
    rows = list_compute_provider_entities(
        db,
        capability=job.capability,
        status="active",
        initiator_entity_id=job.initiator_entity_id,
        mesh_filter=True,
    )
    rep_map = load_compute_provider_reputation_map(db)
    rep_weight = float(
        (get_rewards_config().get("compute_provider") or {}).get("reputation_scheduler_weight", 0.15)
    )
    candidates: list[ComputeProviderCandidate] = []
    for row in rows:
        profile = row["compute_profile"]
        endpoints = profile.get("endpoints") or {}
        base_url = str(endpoints.get("base_url") or "").strip() or None
        owner_id = (profile.get("accountability") or {}).get("owner_entity_id")
        score = 0.5
        if initiator and owner_id == initiator.id:
            score += 2.0
        elif initiator and row["entity_id"] == initiator.id:
            score += 1.5
        if initiator and row["entity_id"] == initiator.owner_id:
            score += 1.0
        score += rep_map.get(row["entity_id"], 0.0) * rep_weight

        offer = next((o for o in profile.get("offers") or [] if o.get("capability") == job.capability), {})
        models = offer.get("models") or []
        adapters = offer.get("adapters") or []
        requested_model = job.constraints.get("model")
        if requested_model and requested_model not in models and models:
            continue

        candidates.append(
            ComputeProviderCandidate(
                source="entity",
                provider_entity_id=row["entity_id"],
                provider_node_id=None,
                base_url=base_url,
                trust_weight=score,
                adapter=str(adapters[0]) if adapters else None,
                model=str(models[0]) if models else requested_model,
                region=str((profile.get("capacity") or {}).get("region") or ""),
                rank_score=score,
                metadata={"entity_type": row["entity_type"], "name": row["name"]},
            )
        )
    return candidates


def _peer_candidates(job: ComputeJob) -> list[ComputeProviderCandidate]:
    if job.capability not in ("witness", "llm_inference", "mcp_host"):
        return []
    peers = load_peer_compute_nodes()
    out: list[ComputeProviderCandidate] = []
    for peer in peers:
        out.append(
            ComputeProviderCandidate(
                source="peer_node",
                provider_entity_id=None,
                provider_node_id=peer.node_id,
                base_url=peer.base_url,
                trust_weight=float(peer.trust_weight),
                adapter=peer.default_provider,
                rank_score=float(peer.trust_weight),
                metadata={"witness_path": peer.witness_path},
            )
        )
    return out


def list_compute_candidates(db: Session, job: ComputeJob) -> list[ComputeProviderCandidate]:
    initiator = db.get(Entity, job.initiator_entity_id) if job.initiator_entity_id else None
    candidates: list[ComputeProviderCandidate] = []

    local = _local_node_candidate(job)
    if local:
        candidates.append(local)

    candidates.extend(_entity_candidates(db, job, initiator))
    candidates.extend(_peer_candidates(job))

    # Rank: local owner entity > local node > entity score > peer trust
    def sort_key(c: ComputeProviderCandidate) -> tuple:
        local_owner = 0
        if c.source == "entity" and initiator and c.provider_entity_id == initiator.id:
            local_owner = 1
        local_node = 1 if c.source == "local_node" else 0
        return (local_owner, local_node, c.rank_score, c.trust_weight)

    candidates.sort(key=sort_key, reverse=True)
    return candidates


def select_compute_provider(db: Session, job: ComputeJob) -> ComputeProviderCandidate | None:
    candidates = list_compute_candidates(db, job)
    if not candidates:
        return None

    registry = load_compute_registry()
    strategy = (registry.get("routing_policy") or {}).get("default") or "ranked"
    if strategy == "peer_round_robin" and job.capability in ("witness", "llm_inference"):
        peer = select_peer_compute_node()
        if peer:
            for candidate in candidates:
                if candidate.source == "peer_node" and candidate.provider_node_id == peer.node_id:
                    return candidate

    return candidates[0]


def schedule_compute_job(db: Session, job: ComputeJob) -> dict[str, Any]:
    """Select provider and emit advisory receipt (execution is caller responsibility in v0.1)."""
    from services.compute_jobs import create_job_record

    selected = select_compute_provider(db, job)
    if selected is None:
        return {
            "status": "no_provider",
            "capability": job.capability,
            "candidates": [],
            "advisory_only": True,
        }

    receipt = build_compute_receipt(
        provider_entity_id=selected.provider_entity_id,
        provider_node_id=selected.provider_node_id,
        capability=job.capability,
        adapter=selected.adapter,
        model=selected.model or job.constraints.get("model"),
        contribution_id=job.contribution_id,
        task_id=job.task_id,
        initiator_entity_id=job.initiator_entity_id,
        input_material=job.constraints.get("input_preview"),
        extra={
            "source": selected.source,
            "base_url": selected.base_url,
            "rank_score": selected.rank_score,
        },
    )

    job_record = create_job_record(
        db,
        capability=job.capability,
        initiator_entity_id=job.initiator_entity_id,
        contribution_id=job.contribution_id,
        task_id=job.task_id,
        constraints=job.constraints,
        selected_provider={
            "source": selected.source,
            "provider_entity_id": selected.provider_entity_id,
            "provider_node_id": selected.provider_node_id,
            "base_url": selected.base_url,
            "adapter": selected.adapter,
            "model": selected.model,
            "trust_weight": selected.trust_weight,
        },
        receipt=receipt,
        status="scheduled",
    )

    return {
        **job_record,
        "candidate_count": len(list_compute_candidates(db, job)),
    }
