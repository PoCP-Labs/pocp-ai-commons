"""Rule-based neural routing — public reference (CI-5)."""

from services.neural.base import ExecutionPlan, NeuralRouter, RoutingRequest, RoutingStep
from services.neural.rule_based_router import (
    RuleBasedNeuralRouter,
    execution_plan_to_dict,
)

__all__ = [
    "ExecutionPlan",
    "NeuralRouter",
    "RoutingRequest",
    "RoutingStep",
    "RuleBasedNeuralRouter",
    "execution_plan_to_dict",
]
