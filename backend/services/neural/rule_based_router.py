from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from models.entity import Entity, EntityType
from services.capability.registry import descriptor_from_record, search_capabilities

from .base import ExecutionPlan, RoutingRequest, RoutingStep

# Map routing-step labels to registry capability_type values (rule-based, no optimizer).
CAPABILITY_TYPE_ALIASES: dict[str, str] = {
    "task_planning": "reasoning",
    "code_review": "review",
    "reasoning": "reasoning",
    "gpu_inference": "gpu_inference",
    "compute_verification": "verification",
    "general_task_execution": "general",
    "human_review": "review",
}

ENTITY_TYPE_MAP: dict[str, EntityType] = {
    "human": EntityType.human,
    "agent": EntityType.agent,
    "skill": EntityType.skill,
    "tool": EntityType.tool,
    "llm": EntityType.llm,
    "workflow": EntityType.workflow,
    "compute_node": EntityType.compute_node,
    "verifier_node": EntityType.verifier_node,
    "reviewer_node": EntityType.reviewer_node,
}


class RuleBasedNeuralRouter:
    """Public reference router.

    This is intentionally simple and explainable.
    Commercial neural routing optimizers should live outside the public core.
    """

    def route(self, request: RoutingRequest) -> ExecutionPlan:
        task_type = request.task_type.lower().strip()

        if task_type in {"code", "coding", "code_review"}:
            steps = [
                RoutingStep(1, "agent", "task_planning", reason="Plan the code task."),
                RoutingStep(2, "skill", "code_review", reason="Review code changes."),
                RoutingStep(3, "llm", "reasoning", reason="Assist with reasoning."),
                RoutingStep(4, "reviewer_node", "human_review", reason="Human final review."),
            ]
        elif task_type in {"compute", "inference", "training"}:
            steps = [
                RoutingStep(1, "compute_node", "gpu_inference", reason="Provide compute."),
                RoutingStep(2, "verifier_node", "compute_verification", reason="Verify compute result."),
            ]
        else:
            steps = [
                RoutingStep(1, "agent", "general_task_execution", reason="General task execution."),
                RoutingStep(2, "reviewer_node", "human_review", reason="Human final review."),
            ]

        return ExecutionPlan(
            task_id=request.task_id,
            steps=steps,
            estimated_cost={"AIC": 10.0, "CC": 0.0, "PT": 0.0},
            risk_level="medium",
            explanation="Rule-based public reference routing plan.",
        )

    def resolve_capabilities(
        self,
        db: Session,
        plan: ExecutionPlan,
        *,
        availability: str = "available",
    ) -> ExecutionPlan:
        """Bind each routing step to the first matching registry capability (CI-5)."""
        resolved: list[RoutingStep] = []
        for step in plan.steps:
            registry_type = CAPABILITY_TYPE_ALIASES.get(step.capability_type, step.capability_type)
            candidates = search_capabilities(
                db,
                capability_type=registry_type,
                availability=availability,
                limit=50,
            )
            expected_entity_type = ENTITY_TYPE_MAP.get(step.entity_type)
            match = None
            for row in candidates:
                if expected_entity_type is None:
                    match = row
                    break
                entity = db.get(Entity, row.entity_id)
                if entity and entity.entity_type == expected_entity_type:
                    match = row
                    break
            if match is None and candidates:
                match = candidates[0]

            capability_id = None
            entity_id = None
            if match is not None:
                desc = descriptor_from_record(match)
                capability_id = desc.capability_id
                entity_id = desc.entity_id

            resolved.append(
                RoutingStep(
                    step=step.step,
                    entity_type=step.entity_type,
                    capability_type=step.capability_type,
                    entity_id=entity_id,
                    capability_id=capability_id,
                    reason=step.reason,
                )
            )
        return ExecutionPlan(
            task_id=plan.task_id,
            steps=resolved,
            estimated_cost=plan.estimated_cost,
            risk_level=plan.risk_level,
            explanation=plan.explanation,
        )

    def route_with_search(
        self,
        db: Session,
        request: RoutingRequest,
        *,
        availability: str = "available",
    ) -> ExecutionPlan:
        """Rule-based route then resolve capabilities from the public registry."""
        plan = self.route(request)
        return self.resolve_capabilities(db, plan, availability=availability)


def execution_plan_to_dict(plan: ExecutionPlan) -> dict[str, Any]:
    return {
        "task_id": plan.task_id,
        "steps": [
            {
                "step": s.step,
                "entity_type": s.entity_type,
                "capability_type": s.capability_type,
                "entity_id": s.entity_id,
                "capability_id": s.capability_id,
                "reason": s.reason,
            }
            for s in plan.steps
        ],
        "estimated_cost": plan.estimated_cost,
        "risk_level": plan.risk_level,
        "explanation": plan.explanation,
        "router": "rule_based_v1",
        "spec_version": "0.3",
    }
