"""Capability-layer engine facades — delegate to existing services without duplication."""

from __future__ import annotations

import os
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from intelligence.protocol import CapabilityModule
from intelligence.governance import run_governance_summary
from models.contribution import ContributionEvent, ContributionParticipant
from models.entity import Entity, EntityStatus, EntityType
from models.invocation import InvocationStep, InvocationTrace
from models.skill import Skill
from models.task import Task
from models.wallet import ReputationScore, Wallet
from services.anti_abuse import (
    check_daily_ai_burn_limit,
    check_daily_contribution_limit,
    require_evidence,
)
from services.clarion import build_clarion_review_packet
from services.graph import build_contribution_graph
from services.reward_advisory import build_reward_advisory
from services.agent_runtimes.study_agent_runtime import langgraph_available
from services.embedding_match import blend_keyword_and_embedding, embedding_provider, ollama_embeddings_enabled
from services.graph_analytics import build_graph_analytics
from services.contribution_dedup import find_semantic_duplicates
from services.verifiers import MultiVerifierService


def module_registry() -> list[dict[str, Any]]:
    openai = bool(os.getenv("OPENAI_API_KEY"))
    deepseek = bool(os.getenv("DEEPSEEK_API_KEY"))
    ollama = os.getenv("ENABLE_OLLAMA_VERIFIER", "false").lower() == "true"
    vllm = os.getenv("ENABLE_VLLM_VERIFIER", "false").lower() == "true"
    llama_cpp = os.getenv("ENABLE_LLAMA_CPP_VERIFIER", "false").lower() == "true"
    crewai = os.getenv("ENABLE_CREWAI_WITNESS", "false").lower() == "true"
    embed = embedding_provider()

    return [
        {
            "module": CapabilityModule.verification.value,
            "status": "active",
            "providers": [
                "mock",
                "openai" if openai else None,
                "deepseek" if deepseek else None,
                "ollama" if ollama else None,
                "vllm" if vllm else None,
                "llama_cpp" if llama_cpp else None,
                "crewai" if crewai else None,
            ],
            "auto_finalization": os.getenv("ENABLE_AUTO_FINALIZATION", "").lower() in ("true", "1", "yes", "on"),
        },
        {"module": CapabilityModule.reputation.value, "status": "active"},
        {
            "module": CapabilityModule.matching.value,
            "status": "active",
            "strategy": "semantic_reputation_v0.5" if embed else "semantic_reputation_v0.3",
            "embedding_provider": embed,
        },
        {"module": CapabilityModule.rewards.value, "status": "active", "source": "verifier_consensus+clarion"},
        {
            "module": CapabilityModule.anti_abuse.value,
            "status": "active",
            "semantic_dedup": embed is not None,
        },
        {
            "module": CapabilityModule.graph.value,
            "status": "active",
            "analytics": "/api/v1/intelligence/graph/analytics",
            "gnn_method": "pagerank_v0.1",
        },
        {"module": CapabilityModule.review_assistant.value, "status": "active", "agent": "Clarion-0"},
        {"module": CapabilityModule.governance.value, "status": "active", "source": "governance_summary"},
        {"module": CapabilityModule.external_api.value, "status": "active"},
        {
            "module": "agent_runtime",
            "status": "active",
            "study_agent": "state_machine_v1",
            "langgraph": langgraph_available(),
            "endpoint": "/api/v1/intelligence/agents/study/run",
        },
        {
            "module": "distributed_compute",
            "status": "active",
            "endpoint": "/api/v1/intelligence/compute/status",
            "scheduler": "/api/v1/compute/jobs",
            "provider_registry": "/api/v1/compute/providers",
            "peer_routing": os.getenv("ENABLE_PEER_COMPUTE", "").lower() in ("true", "1", "yes", "on"),
            "peer_witness": "/api/v1/intelligence/compute/witness",
        },
    ]


async def run_verification(db: Session, contribution: ContributionEvent) -> dict:
    from models.contribution import ContributionStatus
    from services.compute_executor import begin_witness_job
    from services.finalization import evaluate_finalization_policy, try_auto_finalize_after_verify, witness_diversity_summary

    witness_schedule = await begin_witness_job(
        db,
        contribution_id=contribution.id,
        initiator_entity_id=contribution.primary_entity_id,
        context_preview=(contribution.description or "")[:500],
    )

    service = MultiVerifierService()
    consensus = await service.verify_contribution(db, contribution)
    from services.compute_jobs import list_jobs_for_contribution

    consensus["witness_diversity"] = witness_diversity_summary(consensus)
    consensus["distributed_compute"] = {
        "witness_job": witness_schedule,
        "principle": "Entity-attached compute; scheduler + receipts in Proof (v0.2 β)",
        "compute_jobs": list_jobs_for_contribution(db, contribution.id),
    }
    if contribution.status == ContributionStatus.ai_verified:
        auto = try_auto_finalize_after_verify(db, contribution, consensus)
        if auto is not None:
            consensus["finalization"] = auto
        verdict = evaluate_finalization_policy(consensus)
        consensus["verdict"] = verdict
    return consensus


def run_graph(db: Session) -> dict:
    return build_contribution_graph(db)


def run_graph_analytics(db: Session, *, review_limit: int = 20) -> dict:
    return build_graph_analytics(db, review_limit=review_limit)


def run_dedup_check(
    db: Session,
    *,
    entity_id: str | None,
    description: str | None,
    evidence: dict | None,
    exclude_contribution_id: str | None = None,
) -> dict[str, Any]:
    hints = find_semantic_duplicates(
        db,
        entity_id=entity_id,
        description=description,
        evidence=evidence,
        exclude_contribution_id=exclude_contribution_id,
    )
    return {
        "advisory_only": True,
        "embedding_provider": embedding_provider(),
        "duplicate_hints": hints,
        "threshold": float(os.getenv("POCP_SEMANTIC_DEDUP_THRESHOLD", "0.88")),
    }


def run_anti_abuse_precheck(db: Session, *, entity_id: str, evidence: dict | None) -> None:
    require_evidence(evidence)
    check_daily_contribution_limit(db, entity_id)
    if os.getenv("ENABLE_SEMANTIC_DEDUP_BLOCK", "false").lower() == "true":
        hints = find_semantic_duplicates(
            db, entity_id=entity_id, description=None, evidence=evidence
        )
        if hints:
            from fastapi import HTTPException

            raise HTTPException(
                status_code=409,
                detail={
                    "message": "Possible semantic duplicate contribution",
                    "duplicate_hints": hints,
                },
            )


def run_review_assistant(db: Session, contribution: ContributionEvent) -> dict:
    return build_clarion_review_packet(db, contribution)


def run_reward_advisory(db: Session, contribution: ContributionEvent) -> dict:
    return build_reward_advisory(db, contribution)


def _task_keywords(task: Task | None) -> set[str]:
    if not task:
        return set()
    text = f"{task.title} {task.description or ''}".lower()
    return {word for word in text.replace(",", " ").split() if len(word) > 2}


def _keyword_score(entity: Entity, keywords: set[str]) -> float:
    if not keywords:
        return 0.0
    blob = f"{entity.name} {entity.description or ''}".lower()
    hits = sum(1 for word in keywords if word in blob)
    return min(1.0, hits / len(keywords))


def _invocation_activity(db: Session, entity_id: str, task_id: str | None) -> float:
    q = db.query(func.count(InvocationStep.id)).filter(InvocationStep.target_entity_id == entity_id)
    if task_id:
        trace_ids = [
            row[0]
            for row in db.query(InvocationTrace.id).filter(InvocationTrace.task_id == task_id).all()
        ]
        if trace_ids:
            q = q.filter(InvocationStep.trace_id.in_(trace_ids))
    count = q.scalar() or 0
    return min(1.0, count / 5.0)


def _entity_tags(entity: Entity) -> set[str]:
    meta = entity.metadata_ or {}
    tags = meta.get("tags") or []
    caps = meta.get("capabilities") or []
    return {str(t).lower() for t in [*tags, *caps]}


def _contribution_type_keywords(contribution_type: str | None) -> set[str]:
    if not contribution_type:
        return set()
    return {w for w in contribution_type.replace("_", " ").lower().split() if len(w) > 2}


def _semantic_fit(
    entity: Entity,
    *,
    task_keywords: set[str],
    contribution_type: str | None,
    skill_prompts: dict[str, str | None],
) -> float:
    blob = f"{entity.name} {entity.description or ''}".lower()
    if entity.id in skill_prompts and skill_prompts[entity.id]:
        blob += " " + skill_prompts[entity.id].lower()

    tags = _entity_tags(entity)
    type_kw = _contribution_type_keywords(contribution_type)
    pool = task_keywords | type_kw | tags
    if not pool:
        return 0.0

    hits = sum(1 for token in pool if token in blob or token in tags)
    keyword_score = min(1.0, hits / max(len(pool), 1))
    query = " ".join(sorted(pool))
    return blend_keyword_and_embedding(keyword_score, query, blob)


def run_matching(
    db: Session,
    *,
    task_id: str | None = None,
    contribution_type: str | None = None,
    limit: int = 5,
) -> dict[str, Any]:
    """Rank agents and skills: reputation + semantic fit + invocation history (v0.3)."""
    task = db.query(Task).filter(Task.id == task_id).first() if task_id else None
    task_keywords = _task_keywords(task)
    skill_prompts = {s.entity_id: s.prompt_template for s in db.query(Skill).all()}

    rep_totals: dict[str, float] = {}
    for row in db.query(ReputationScore).all():
        rep_totals[row.entity_id] = rep_totals.get(row.entity_id, 0.0) + row.score

    max_rep = max(rep_totals.values(), default=1.0) or 1.0

    agents = (
        db.query(Entity)
        .filter(Entity.entity_type == EntityType.agent, Entity.status == EntityStatus.active)
        .all()
    )
    skills = (
        db.query(Entity)
        .filter(Entity.entity_type == EntityType.skill, Entity.status == EntityStatus.active)
        .all()
    )

    def score_entity(entity: Entity) -> tuple[float, dict]:
        rep_norm = rep_totals.get(entity.id, 0.0) / max_rep
        sem = _semantic_fit(
            entity,
            task_keywords=task_keywords,
            contribution_type=contribution_type,
            skill_prompts=skill_prompts,
        )
        inv = _invocation_activity(db, entity.id, task_id)
        total = round(0.35 * rep_norm + 0.40 * sem + 0.25 * inv, 4)
        return total, {
            "reputation": round(rep_totals.get(entity.id, 0.0), 2),
            "semantic_fit": round(sem, 2),
            "invocation_activity": round(inv, 2),
            "match_score": total,
            "tags": sorted(_entity_tags(entity)),
        }

    def rank(entities: list[Entity]) -> list[dict]:
        scored = sorted(entities, key=lambda e: score_entity(e)[0], reverse=True)
        out = []
        for entity in scored[:limit]:
            _, breakdown = score_entity(entity)
            out.append(
                {
                    "entity_id": entity.id,
                    "name": entity.name,
                    "entity_type": entity.entity_type.value,
                    "can_contribute": True,
                    **breakdown,
                }
            )
        return out

    from services.compute_matching import recommend_compute_providers

    compute_match = recommend_compute_providers(
        db,
        task_id=task_id,
        contribution_type=contribution_type,
        limit_per_capability=max(2, limit // 2),
    )

    return {
        "task_id": task_id,
        "task_title": task.title if task else None,
        "contribution_type": contribution_type,
        "task_keywords": sorted(task_keywords),
        "recommended_agents": rank(agents),
        "recommended_skills": rank(skills),
        "required_capabilities": compute_match["required_capabilities"],
        "recommended_compute_providers": compute_match["recommended_compute_providers"],
        "compute_by_capability": compute_match["by_capability"],
        "strategy": "semantic_reputation_compute_v0.6" if embedding_provider() else "semantic_reputation_compute_v0.4",
        "embedding_provider": embedding_provider(),
        "advisory_only": True,
    }


def run_governance(db: Session) -> dict[str, Any]:
    return run_governance_summary(db)


def entity_intelligence_profile(db: Session, entity_id: str) -> dict | None:
    entity = db.query(Entity).filter(Entity.id == entity_id).first()
    if not entity:
        return None

    wallet = db.query(Wallet).filter(Wallet.entity_id == entity_id).first()
    reputation = db.query(ReputationScore).filter(ReputationScore.entity_id == entity_id).all()

    as_primary = (
        db.query(ContributionEvent)
        .filter(ContributionEvent.primary_entity_id == entity_id)
        .count()
    )
    as_participant = (
        db.query(ContributionParticipant)
        .filter(ContributionParticipant.entity_id == entity_id)
        .count()
    )

    return {
        "entity": {
            "id": entity.id,
            "entity_type": entity.entity_type.value,
            "name": entity.name,
            "description": entity.description,
            "status": entity.status.value,
            "metadata": entity.metadata_ or {},
            "can_contribute": True,
        },
        "wallet": {
            "cp_balance": wallet.cp_balance if wallet else 0,
            "ai_credits": wallet.ai_credits if wallet else 0,
        }
        if wallet
        else None,
        "reputation": [
            {"category": r.category, "score": r.score} for r in reputation
        ],
        "contribution_stats": {
            "as_primary": as_primary,
            "as_participant": as_participant,
            "total_touchpoints": as_primary + as_participant,
        },
        "compute_profile": (entity.metadata_ or {}).get("compute_profile"),
        "compute_provider_reputation": round(
            next(
                (r.score for r in reputation if r.category == "compute_provider"),
                0.0,
            ),
            2,
        ),
        "principle": "Every entity participates through verified contribution events.",
    }


def build_intelligence_packet(db: Session, contribution_id: str) -> dict | None:
    contribution = (
        db.query(ContributionEvent)
        .options(
            joinedload(ContributionEvent.task),
            joinedload(ContributionEvent.participants),
            joinedload(ContributionEvent.ai_verifications),
            joinedload(ContributionEvent.human_reviews),
        )
        .filter(ContributionEvent.id == contribution_id)
        .first()
    )
    if not contribution:
        return None

    participants = []
    for p in contribution.participants:
        ent = db.query(Entity).filter(Entity.id == p.entity_id).first()
        participants.append(
            {
                "entity_id": p.entity_id,
                "name": ent.name if ent else p.entity_id,
                "entity_type": ent.entity_type.value if ent else "unknown",
                "role": p.role.value if hasattr(p.role, "value") else str(p.role),
                "weight": p.weight,
            }
        )

    return {
        "contribution_id": contribution.id,
        "status": contribution.status.value,
        "description": contribution.description,
        "participants": participants,
        "verification": {
            "ai_results": [
                {
                    "provider": v.model_provider,
                    "score": v.score,
                    "passed": v.passed,
                    "feedback": v.feedback,
                }
                for v in contribution.ai_verifications
            ],
            "human_reviews": [
                {
                    "reviewer_id": r.reviewer_id,
                    "approved": r.approved,
                    "feedback": r.feedback,
                }
                for r in contribution.human_reviews
            ],
        },
        "reward_advisory": run_reward_advisory(db, contribution),
        "review_assistant": run_review_assistant(db, contribution),
        "advisory_only": True,
        "finalization": "traceable_policy_or_manual",
    }


async def run_study_agent(db: Session, **kwargs) -> dict:
    """Agent runtime facade — StudyAgent graph + InvocationTrace (capability layer)."""
    from services.study_agent import execute_study_agent

    return await execute_study_agent(db, **kwargs)


def run_list_compute_providers(
    db: Session,
    *,
    capability: str | None = None,
    status: str = "active",
    initiator_entity_id: str | None = None,
    organization_entity_id: str | None = None,
    mesh_filter: bool = False,
) -> dict:
    from services.compute_profile import list_compute_provider_entities
    from services.compute_reputation import load_compute_provider_reputation_map

    providers = list_compute_provider_entities(
        db,
        capability=capability,
        status=status,
        initiator_entity_id=initiator_entity_id,
        organization_entity_id=organization_entity_id,
        mesh_filter=mesh_filter,
    )
    rep_map = load_compute_provider_reputation_map(db)
    for row in providers:
        row["compute_provider_reputation"] = round(rep_map.get(row["entity_id"], 0.0), 2)
    return {
        "spec_version": "0.1",
        "provider_count": len(providers),
        "providers": providers,
        "mesh_filter": mesh_filter,
        "organization_entity_id": organization_entity_id,
        "advisory_only": True,
    }


def run_register_compute_profile(
    db: Session,
    *,
    entity_id: str,
    profile: dict,
    owner_entity_id: str | None,
):
    from services.compute_profile import register_compute_profile

    return register_compute_profile(
        db,
        entity_id,
        profile,
        owner_entity_id=owner_entity_id,
    )


def run_heartbeat_compute_profile(
    db: Session,
    *,
    entity_id: str,
    status: str,
    owner_entity_id: str | None,
):
    from services.compute_profile import heartbeat_compute_profile

    return heartbeat_compute_profile(
        db,
        entity_id,
        status=status,
        owner_entity_id=owner_entity_id,
    )


def run_schedule_compute_job(
    db: Session,
    *,
    capability: str,
    initiator_entity_id: str | None,
    contribution_id: str | None,
    task_id: str | None,
    constraints: dict | None,
) -> dict:
    from services.compute_scheduler import ComputeJob, schedule_compute_job

    job = ComputeJob(
        capability=capability,
        initiator_entity_id=initiator_entity_id,
        contribution_id=contribution_id,
        task_id=task_id,
        constraints=constraints or {},
    )
    return schedule_compute_job(db, job)


def run_get_compute_job(db: Session, job_id: str) -> dict:
    from services.compute_jobs import get_job_record

    return get_job_record(db, job_id)
