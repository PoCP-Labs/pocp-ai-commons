"""Contribution-to-rights conversion — versioned protocol rules (pocp.rights_rules.v0.1).

Maps verified contribution participants to CP, AI Credits (BC), and Reputation
using instance config (backend/config/pocp_rewards.yaml). Proof packets embed
a conversion snapshot so federated peers can recompute allocations.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from models.contribution import ContributionEvent, ContributionParticipant, ParticipantRole
from models.entity import Entity, EntityType
from services.protocol_config import get_rewards_config
from services.rights import RightPolicy, rights_policy

RIGHTS_RULES_SCHEMA = "pocp.rights_rules.v0.1"
CONVERSION_SCHEMA = "pocp.contribution_to_rights_conversion.v0.1"


def rights_rules_manifest() -> dict[str, Any]:
    """Export active rights rules for this node (federation recompute input)."""
    config = get_rewards_config()
    policies = rights_policy()
    return {
        "schema": RIGHTS_RULES_SCHEMA,
        "rules_version": config.get("spec_version", "0.1"),
        "registration": dict(config.get("registration") or {}),
        "rights": {kind: asdict(policy) for kind, policy in policies.items()},
        "contribution_defaults": dict(config.get("contribution_defaults") or {}),
        "federation": dict(config.get("federation") or {}),
        "portability": {
            "bc_transferable": False,
            "cp_transferable": False,
            "reputation_portable_via_proof": True,
            "note": "BC/CP are instance-local; reputation may import via signed proof.",
        },
    }


def _human_rights_plan(participant: ContributionParticipant) -> dict[str, float] | None:
    if participant.role not in (ParticipantRole.creator, ParticipantRole.executor):
        return None
    defaults = get_rewards_config()["contribution_defaults"]["human"]
    cp_base = float(defaults["cp_base"])
    bc_base = float(defaults["ai_credits_base"])
    weight = participant.weight or 0.4
    scale = weight / 0.4
    return {
        "cp": round(cp_base * scale, 2),
        "bc": round(bc_base * scale, 2),
    }


def _reputation_plan(entity_type: EntityType, participant: ContributionParticipant) -> float | None:
    defaults = get_rewards_config()["contribution_defaults"]
    if entity_type == EntityType.skill and participant.role == ParticipantRole.skill_provider:
        base = float(defaults["skill"]["reputation_base"])
        weight = participant.weight or 0.15
        return round(base * weight / 0.15, 2) if weight else base
    if entity_type == EntityType.agent and participant.role in (
        ParticipantRole.executor,
        ParticipantRole.creator,
    ):
        base = float(defaults["agent"]["reputation_base"])
        weight = participant.weight or 0.25
        return round(base * weight / 0.25, 2) if weight else base
    return None


def plan_participant_allocation(
    participant: ContributionParticipant,
    entity: Entity | None,
) -> dict[str, Any]:
    """Deterministic rights plan for one participant (no DB writes)."""
    if entity is None:
        return {
            "entity_id": participant.entity_id,
            "role": participant.role.value,
            "weight": participant.weight,
            "grants": [],
            "skipped": "entity_not_found",
        }

    grants: list[dict[str, Any]] = []
    policies = rights_policy()

    if entity.entity_type == EntityType.human:
        amounts = _human_rights_plan(participant)
        if amounts:
            grants.append(
                {
                    "kind": "cp",
                    "version": policies["cp"].version,
                    "amount": amounts["cp"],
                    "spendable": policies["cp"].spendable,
                    "transferable": policies["cp"].transferable,
                }
            )
            grants.append(
                {
                    "kind": "bc",
                    "version": policies["bc"].version,
                    "amount": amounts["bc"],
                    "spendable": policies["bc"].spendable,
                    "transferable": policies["bc"].transferable,
                }
            )
    else:
        rep = _reputation_plan(entity.entity_type, participant)
        bc_amount = None
        if entity.entity_type == EntityType.agent:
            from services.rights import entity_bc_amount

            bc_amount = entity_bc_amount(entity.entity_type, participant)
        elif entity.entity_type == EntityType.skill:
            from services.rights import entity_bc_amount

            bc_amount = entity_bc_amount(entity.entity_type, participant)
        if bc_amount:
            grants.append(
                {
                    "kind": "bc",
                    "version": policies["bc"].version,
                    "amount": bc_amount,
                    "spendable": policies["bc"].spendable,
                    "transferable": policies["bc"].transferable,
                }
            )
        if rep is not None:
            grants.append(
                {
                    "kind": "reputation",
                    "category": entity.entity_type.value,
                    "amount": rep,
                    "spendable": False,
                    "transferable": False,
                }
            )

    return {
        "entity_id": entity.id,
        "entity_type": entity.entity_type.value,
        "entity_name": entity.name,
        "role": participant.role.value,
        "weight": participant.weight,
        "grants": grants,
    }


def plan_contribution_rights(
    contribution: ContributionEvent,
    entities: dict[str, Entity],
) -> list[dict[str, Any]]:
    return [
        plan_participant_allocation(p, entities.get(p.entity_id))
        for p in contribution.participants
    ]


def build_contribution_to_rights_conversion(
    contribution: ContributionEvent,
    entities: dict[str, Entity],
    *,
    applied_rewards: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Proof-packet block: rules version + planned + applied snapshot."""
    config = get_rewards_config()
    planned = plan_contribution_rights(contribution, entities)
    return {
        "schema": CONVERSION_SCHEMA,
        "rules_schema": RIGHTS_RULES_SCHEMA,
        "rules_version": config.get("spec_version", "0.1"),
        "contribution_id": contribution.id,
        "status": contribution.status.value,
        "planned_allocations": planned,
        "applied_rewards": applied_rewards,
        "recomputable": True,
    }


def reputation_amount_for_participant(
    entity: Entity,
    participant: ContributionParticipant,
) -> float | None:
    """Shared helper for contribution approval (matches plan)."""
    return _reputation_plan(entity.entity_type, participant)
