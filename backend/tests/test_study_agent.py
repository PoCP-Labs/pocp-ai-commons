import asyncio
import os
import unittest

from services.agent_runtimes.study_agent_runtime import langgraph_available, run_study_agent_graph


class StudyAgentRuntimeTests(unittest.TestCase):
    def test_langgraph_disabled_by_default(self):
        prev = os.environ.get("ENABLE_LANGGRAPH_STUDY_AGENT")
        os.environ["ENABLE_LANGGRAPH_STUDY_AGENT"] = "false"
        try:
            self.assertFalse(langgraph_available())
        finally:
            if prev is None:
                os.environ.pop("ENABLE_LANGGRAPH_STUDY_AGENT", None)
            else:
                os.environ["ENABLE_LANGGRAPH_STUDY_AGENT"] = prev

    def test_state_machine_produces_draft(self):
        async def fake_llm(prompt: str):
            return ("Draft notes for test.", "mock", "mock-chat")

        result = asyncio.run(
            run_study_agent_graph(
                topic="R matrices",
                skill_prompt="Structure R study notes.",
                llm_invoke=fake_llm,
            )
        )
        self.assertEqual(result.runtime, "state_machine_v1")
        self.assertIn("Draft notes", result.draft)
        self.assertEqual(len(result.steps), 3)
        self.assertEqual(result.steps[-1].node, "llm_invoke")


class StudyAgentEvidenceTests(unittest.TestCase):
    def test_build_evidence_links_trace_and_draft(self):
        from services.study_agent import build_study_agent_evidence

        run = {
            "trace_id": "trace-abc",
            "topic": "R matrices",
            "runtime": "state_machine_v1",
            "draft": "Matrix notes content here.",
            "graph_steps": [{"node": "plan", "summary": "plan"}],
            "invocation_chain": [{"action": "invokes_llm"}],
            "model_provider": "mock",
        }
        evidence = build_study_agent_evidence(run)
        self.assertIn("Matrix notes", evidence["content_preview"])
        self.assertEqual(evidence["study_agent"]["trace_id"], "trace-abc")
        self.assertEqual(evidence["agents_used"], ["StudyAgent"])


if __name__ == "__main__":
    unittest.main()
