"""Agent Studio — self-learning orchestration for Meta Agents."""

from services.agent_studio.evolution import (
    apply_proposal,
    get_learning_profile,
    process_outcome,
    review_proposal,
    studio_dashboard,
)
from services.agent_studio.handoffs import complete_handoff, create_handoff, list_handoffs
from services.agent_studio.mission_plans import (
    create_mission_from_plan,
    list_mission_plans,
    spawn_plan_handoffs,
)
from services.agent_studio.missions import activate_mission, create_mission, get_mission, list_missions
from services.agent_studio.outcomes import record_outcome
from services.agent_studio.proposals import list_proposals

__all__ = [
    "activate_mission",
    "apply_proposal",
    "complete_handoff",
    "create_handoff",
    "create_mission",
    "create_mission_from_plan",
    "list_mission_plans",
    "spawn_plan_handoffs",
    "get_learning_profile",
    "get_mission",
    "list_handoffs",
    "list_missions",
    "list_proposals",
    "process_outcome",
    "record_outcome",
    "review_proposal",
    "studio_dashboard",
]
