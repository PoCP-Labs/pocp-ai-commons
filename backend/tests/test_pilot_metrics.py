import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.pilot_metrics import (
    PILOT_TARGETS,
    _build_metrics,
    _invocation_chain_depth,
)


class PilotMetricsTests(unittest.TestCase):
    def test_invocation_chain_depth_counts_entities(self):
        trace = {
            "initiator_id": "human-1",
            "steps": [
                {"source_entity_id": "human-1", "target_entity_id": "agent-1", "action": "uses"},
                {"source_entity_id": "agent-1", "target_entity_id": "skill-1", "action": "calls"},
                {"source_entity_id": "skill-1", "target_entity_id": "llm-1", "action": "invokes_llm"},
            ],
        }
        self.assertEqual(_invocation_chain_depth(trace), 4)

    def test_build_metrics_pilot_checks_structure(self):
        now = "2026-05-29T12:00:00+00:00"
        report = _build_metrics(
            source="test",
            days=30,
            health={"status": "ok", "version": "0.3.0"},
            entities=[
                {"id": "h1", "entity_type": "human", "name": "Alice"},
                {"id": "a1", "entity_type": "agent", "name": "Agent"},
                {"id": "s1", "entity_type": "skill", "name": "Skill"},
                {"id": "l1", "entity_type": "llm", "name": "Lumen-0"},
            ],
            contributions=[
                {
                    "id": "c1",
                    "status": "approved",
                    "created_at": now,
                    "primary_entity_id": "h1",
                    "participants": [
                        {"entity_id": "h1", "role": "creator"},
                        {"entity_id": "a1", "role": "executor"},
                        {"entity_id": "s1", "role": "skill_provider"},
                    ],
                    "human_reviews": [{"reviewer_id": "h2", "approved": True}],
                    "ai_verifications": [{"model_provider": "mock"}],
                }
            ],
            invocations=[
                {
                    "initiator_id": "h1",
                    "created_at": now,
                    "steps": [
                        {"source_entity_id": "h1", "target_entity_id": "a1"},
                        {"source_entity_id": "a1", "target_entity_id": "s1"},
                        {"source_entity_id": "s1", "target_entity_id": "l1"},
                    ],
                }
            ],
            compute_status={"active_adapters": ["mock"], "node_id": "test-node", "peer_compute_enabled": False},
            compute_peers=None,
            intelligence_status={
                "modules": [{"module": "contribution_verification", "providers": ["mock", "Lumen-0", "DeSui"]}]
            },
            ledger_verify={"valid": True, "count": 3},
            federation_imports=[],
        )
        self.assertIn("protocol_layer", report)
        self.assertIn("distributed_intelligence_layer", report)
        self.assertIn("distributed_compute_layer", report)
        self.assertEqual(report["protocol_layer"]["active_entities"], 4)
        self.assertEqual(report["protocol_layer"]["active_entity_types"], 4)
        self.assertEqual(report["distributed_intelligence_layer"]["invocation_trace_count"], 1)
        self.assertGreaterEqual(report["distributed_intelligence_layer"]["invocation_depth_avg"], 3.0)
        self.assertEqual(len(report["pilot_checks"]), len(PILOT_TARGETS))
        self.assertFalse(report["pilot_ready"])


if __name__ == "__main__":
    unittest.main()
