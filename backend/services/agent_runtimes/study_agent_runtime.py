"""StudyAgent graph runtime — LangGraph when installed, state-machine fallback (NN-3)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable


@dataclass
class StudyAgentStep:
    node: str
    summary: str
    detail: str = ""


@dataclass
class StudyAgentRunResult:
    runtime: str
    steps: list[StudyAgentStep] = field(default_factory=list)
    draft: str = ""
    model_provider: str = "mock"
    model: str | None = None


LLMInvoke = Callable[[str], Awaitable[tuple[str, str, str]]]


def langgraph_available() -> bool:
    if os.getenv("ENABLE_LANGGRAPH_STUDY_AGENT", "false").lower() != "true":
        return False
    try:
        import langgraph  # noqa: F401

        return True
    except ImportError:
        return False


async def run_study_agent_graph(
    *,
    topic: str,
    skill_prompt: str,
    llm_invoke: LLMInvoke,
    model_provider: str = "mock",
) -> StudyAgentRunResult:
    """Run StudyAgent: plan → skill structure → LLM draft. Uses LangGraph if enabled."""
    if langgraph_available():
        return await _run_langgraph(topic, skill_prompt, llm_invoke, model_provider)
    return await _run_state_machine(topic, skill_prompt, llm_invoke, model_provider)


async def _run_state_machine(
    topic: str,
    skill_prompt: str,
    llm_invoke: LLMInvoke,
    model_provider: str,
) -> StudyAgentRunResult:
    steps: list[StudyAgentStep] = []

    plan = (
        f"Organize study materials for: {topic}. "
        "Break into sections, examples, and practice prompts."
    )
    steps.append(StudyAgentStep(node="plan", summary="StudyAgent planning", detail=plan))

    outline = (
        f"Apply skill template: {skill_prompt[:400]}\n"
        f"Target topic: {topic}\n"
        "Sections: overview, key concepts, worked examples, practice."
    )
    steps.append(StudyAgentStep(node="skill_invoke", summary="Skill structuring", detail=outline))

    prompt = (
        "You are StudyAgent for PoCP AI Commons. Produce concise study notes.\n\n"
        f"Topic: {topic}\n\n"
        f"Skill guidance:\n{skill_prompt}\n\n"
        f"Plan:\n{plan}\n\n"
        "Return structured notes suitable for human review and contribution."
    )
    draft, actual_provider, actual_model = await llm_invoke(prompt)
    steps.append(
        StudyAgentStep(
            node="llm_invoke",
            summary=f"LLM draft via {actual_provider}",
            detail=draft[:500],
        )
    )

    return StudyAgentRunResult(
        runtime="state_machine_v1",
        steps=steps,
        draft=draft,
        model_provider=actual_provider,
        model=actual_model,
    )


async def _run_langgraph(
    topic: str,
    skill_prompt: str,
    llm_invoke: LLMInvoke,
    model_provider: str,
) -> StudyAgentRunResult:
    from typing import TypedDict

    from langgraph.graph import END, StateGraph

    class StudyState(TypedDict, total=False):
        topic: str
        skill_prompt: str
        plan: str
        outline: str
        draft: str
        provider: str
        model: str
        steps: list[dict[str, str]]

    async def plan_node(state: StudyState) -> dict[str, Any]:
        plan = (
            f"Organize study materials for: {state['topic']}. "
            "Break into sections, examples, and practice prompts."
        )
        steps = list(state.get("steps") or [])
        steps.append({"node": "plan", "summary": plan[:200]})
        return {"plan": plan, "steps": steps}

    async def skill_node(state: StudyState) -> dict[str, Any]:
        outline = (
            f"Skill: {state['skill_prompt'][:400]}\n"
            f"Topic: {state['topic']}\n"
            "Sections: overview, concepts, examples, practice."
        )
        steps = list(state.get("steps") or [])
        steps.append({"node": "skill_invoke", "summary": outline[:200]})
        return {"outline": outline, "steps": steps}

    async def llm_node(state: StudyState) -> dict[str, Any]:
        prompt = (
            "You are StudyAgent. Produce concise study notes.\n\n"
            f"Topic: {state['topic']}\n"
            f"Outline:\n{state.get('outline', '')}\n"
            f"Plan:\n{state.get('plan', '')}"
        )
        draft, provider, model = await llm_invoke(prompt)
        steps = list(state.get("steps") or [])
        steps.append({"node": "llm_invoke", "summary": draft[:200]})
        return {"draft": draft, "provider": provider, "model": model, "steps": steps}

    graph = StateGraph(StudyState)
    graph.add_node("plan", plan_node)
    graph.add_node("skill", skill_node)
    graph.add_node("llm", llm_node)
    graph.set_entry_point("plan")
    graph.add_edge("plan", "skill")
    graph.add_edge("skill", "llm")
    graph.add_edge("llm", END)
    app = graph.compile()

    final = await app.ainvoke(
        {"topic": topic, "skill_prompt": skill_prompt, "steps": []},
    )
    steps = [
        StudyAgentStep(node=s["node"], summary=s["summary"], detail=s.get("detail", ""))
        for s in final.get("steps") or []
    ]
    return StudyAgentRunResult(
        runtime="langgraph",
        steps=steps,
        draft=final.get("draft") or "",
        model_provider=final.get("provider") or model_provider,
        model=final.get("model"),
    )
