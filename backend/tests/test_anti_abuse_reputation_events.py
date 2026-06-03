"""CI-10 reputation event-sourcing scaffold tests (Sentinel-0)."""

import unittest
from unittest.mock import patch

from services.anti_abuse import (
    ReputationEvent,
    ReputationGraphIndexer,
    block_reputation_self_feedback,
    reject_commercial_reputation_keys,
    validate_reputation_event,
)


class ReputationEventSecurityTests(unittest.TestCase):
    def test_self_feedback_blocked(self):
        with self.assertRaises(ValueError) as ctx:
            block_reputation_self_feedback("entity-a", "entity-a")
        self.assertIn("Self-feedback", str(ctx.exception))

    def test_valid_event_passes_validation(self):
        event = ReputationEvent(
            event_id="rep_1",
            event_type="SettlementExecuted",
            subject_entity_id="skill-1",
            scope="code_review",
            actor_entity_id="verifier-1",
            source_ref="settlement-abc",
            delta="success",
        )
        validate_reputation_event(event)

    def test_missing_source_ref_rejected(self):
        event = ReputationEvent(
            event_id="rep_2",
            event_type="SettlementExecuted",
            subject_entity_id="skill-1",
            scope="code_review",
            actor_entity_id="verifier-1",
            source_ref="",
            delta="success",
        )
        with self.assertRaises(ValueError):
            validate_reputation_event(event)

    def test_commercial_optimizer_keys_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            reject_commercial_reputation_keys({"ml_rank_weight": 0.9})
        self.assertIn("Commercial", str(ctx.exception))


class ReputationGraphIndexerTests(unittest.TestCase):
    def test_event_sourced_projection(self):
        indexer = ReputationGraphIndexer()
        indexer.ingest(
            event_type="SettlementExecuted",
            subject_entity_id="skill-1",
            scope="code_review",
            actor_entity_id="verifier-1",
            source_ref="settlement-1",
            delta="success",
        )
        indexer.ingest(
            event_type="VerificationCompleted",
            subject_entity_id="skill-1",
            scope="code_review",
            actor_entity_id="verifier-2",
            source_ref="verification-1",
            delta="failure",
        )
        snap = indexer.get_snapshot("skill-1", "code_review")
        self.assertIsNotNone(snap)
        assert snap is not None
        self.assertEqual(snap.success_count, 1)
        self.assertEqual(snap.failure_count, 1)
        self.assertAlmostEqual(snap.score, 0.5)

    def test_replay_matches_incremental_projection(self):
        indexer = ReputationGraphIndexer()
        indexer.ingest(
            event_type="InvocationCompleted",
            subject_entity_id="node-1",
            scope="gpu_inference",
            actor_entity_id="agent-1",
            source_ref="inv-1",
            delta="success",
        )
        before = indexer.get_snapshot("node-1", "gpu_inference")
        replayed = indexer.replay()
        after = replayed[("node-1", "gpu_inference")]
        assert before is not None
        self.assertEqual(before.success_count, after.success_count)
        self.assertEqual(len(indexer.store.events), 1)

    def test_self_feedback_ingest_rejected(self):
        indexer = ReputationGraphIndexer()
        with self.assertRaises(ValueError):
            indexer.ingest(
                event_type="SettlementExecuted",
                subject_entity_id="entity-a",
                scope="review",
                actor_entity_id="entity-a",
                source_ref="settlement-x",
                delta="success",
            )

    def test_unsupported_event_type_rejected(self):
        indexer = ReputationGraphIndexer()
        with self.assertRaises(ValueError) as ctx:
            indexer.ingest(
                event_type="ManualReputationEdit",
                subject_entity_id="skill-1",
                scope="code_review",
                actor_entity_id="verifier-1",
                source_ref="settlement-1",
                delta="success",
            )
        self.assertIn("Unsupported reputation source", str(ctx.exception))

    @patch("services.anti_abuse.DAILY_REPUTATION_EVENT_LIMIT", 1)
    def test_daily_reputation_event_limit(self):
        indexer = ReputationGraphIndexer()
        indexer.ingest(
            event_type="SettlementExecuted",
            subject_entity_id="skill-1",
            scope="code_review",
            actor_entity_id="verifier-1",
            source_ref="settlement-1",
            delta="success",
        )
        with self.assertRaises(ValueError) as ctx:
            indexer.ingest(
                event_type="SettlementExecuted",
                subject_entity_id="skill-1",
                scope="code_review",
                actor_entity_id="verifier-1",
                source_ref="settlement-2",
                delta="success",
            )
        self.assertIn("Daily reputation event limit", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
