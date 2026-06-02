from __future__ import annotations

from .base import ExecutionPlan, RoutingRequest, RoutingStep


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
