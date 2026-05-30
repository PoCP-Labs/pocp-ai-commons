import unittest
from unittest.mock import MagicMock, patch

from intelligence.engines import (
    _contribution_type_keywords,
    _entity_tags,
    _keyword_score,
    _semantic_fit,
    _task_keywords,
)
from intelligence.federation_intel import summarize_federation_ingest
from intelligence.governance import run_governance_summary
from models.entity import Entity, EntityType


class MatchingEngineTests(unittest.TestCase):
    def test_task_keywords_filters_short_words(self):
        task = MagicMock(title="R Language Study", description="Learn vectors and matrices")
        keywords = _task_keywords(task)
        self.assertIn("language", keywords)
        self.assertIn("study", keywords)
        self.assertNotIn("r", keywords)

    def test_keyword_score_matches_description(self):
        entity = MagicMock(
            name="R-Tutor Skill",
            description="R language knowledge structuring capability",
        )
        score = _keyword_score(entity, {"language", "study", "vectors"})
        self.assertGreater(score, 0.0)

    def test_contribution_type_keywords(self):
        keywords = _contribution_type_keywords("code_contribution")
        self.assertIn("code", keywords)
        self.assertIn("contribution", keywords)

    def test_entity_tags_from_metadata(self):
        entity = MagicMock(metadata_={"tags": ["r", "study"], "capabilities": ["tutor"]})
        tags = _entity_tags(entity)
        self.assertIn("r", tags)
        self.assertIn("tutor", tags)

    def test_semantic_fit_uses_tags_and_type(self):
        entity = MagicMock(
            id="skill-1",
            name="Study Helper",
            description="Helps with language learning",
            metadata_={"tags": ["study", "language"]},
        )
        score = _semantic_fit(
            entity,
            task_keywords={"study", "language"},
            contribution_type="documentation",
            skill_prompts={},
        )
        self.assertGreater(score, 0.0)


class FederationIntelTests(unittest.TestCase):
    def test_ingest_summary_advisory(self):
        summary = summarize_federation_ingest(
            {
                "source_node_id": "node-a",
                "contribution_id": "c1",
                "intelligence_packet": {"status": "approved", "participants": [{}, {}]},
                "contribution_proof": {"integrity": {"proof_hash": "abc123"}},
            }
        )
        self.assertTrue(summary["advisory_only"])
        self.assertEqual(summary["source_node_id"], "node-a")
        self.assertEqual(summary["participant_count"], 2)
        self.assertEqual(summary["proof_hash"], "abc123")

    @patch("intelligence.federation_intel.build_contribution_proof_packet")
    @patch("intelligence.federation_intel.build_intelligence_packet")
    def test_export_bundle_shape(self, mock_intel, mock_proof):
        from intelligence.federation_intel import export_federation_intelligence_packet

        mock_intel.return_value = {"contribution_id": "c1", "status": "approved"}
        mock_proof.return_value = {"integrity": {"proof_hash": "xyz"}}
        db = MagicMock()

        packet = export_federation_intelligence_packet(db, "c1", node_id="test-node")
        self.assertEqual(packet["export_type"], "pocp_federation_intelligence_v0.2")
        self.assertEqual(packet["source_node_id"], "test-node")
        self.assertIn("intelligence_packet", packet)
        self.assertIn("contribution_proof", packet)


class GraphLedgerTests(unittest.TestCase):
    def test_ledger_node_prefix_constant(self):
        from services.graph import LEDGER_NODE_PREFIX

        self.assertTrue(LEDGER_NODE_PREFIX.startswith("ledger:"))

    def test_hub_inbound_roles_include_tool_and_data(self):
        from services.graph import _HUB_INBOUND_ROLES
        from models.contribution import ParticipantRole

        self.assertEqual(_HUB_INBOUND_ROLES[ParticipantRole.tool_provider], "provides_tool")
        self.assertEqual(_HUB_INBOUND_ROLES[ParticipantRole.data_provider], "provides_data")
        self.assertEqual(_HUB_INBOUND_ROLES[ParticipantRole.witness], "witnesses")


class GovernanceTests(unittest.TestCase):
    def test_governance_summary_is_advisory(self):
        db = MagicMock()
        db.query.return_value.group_by.return_value.all.return_value = []
        db.query.return_value.filter.return_value.scalar.return_value = 0
        db.query.return_value.scalar.return_value = 0

        summary = run_governance_summary(db)
        self.assertTrue(summary["advisory_only"])
        self.assertTrue(summary["entity_equal_automation"])
        self.assertIn("network_snapshot", summary)


if __name__ == "__main__":
    unittest.main()
