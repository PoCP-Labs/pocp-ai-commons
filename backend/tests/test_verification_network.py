"""CI-8 — verifier_node wiring and standalone verification API sketch."""

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models.contribution import (
    ContributionEvent,
    ContributionParticipant,
    ContributionStatus,
    ParticipantRole,
)
from models.entity import Entity, EntityStatus, EntityType
from models.task import Task, TaskStatus
from services.contribution_dispute import challenge_contribution
from services.contribution_verification_network import (
    attach_verifier_node,
    build_verification_network_manifest,
    resolve_verifier_node,
)
from services.entity.schemas import LOCAL_VERIFIER_NODE_ID
from services.entity_register import register_verifier_node


class VerificationNetworkTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()

        self.human = Entity(id="human-1", entity_type=EntityType.human, name="Alice", status=EntityStatus.active)
        self.challenger = Entity(id="human-2", entity_type=EntityType.human, name="Bob", status=EntityStatus.active)
        self.db.add_all([self.human, self.challenger])
        register_verifier_node(
            self.db,
            entity_id=LOCAL_VERIFIER_NODE_ID,
            name="Local Verifier Node",
            description="Test verifier",
            maintainer_id="human-1",
            verifier_kinds=["ai_review", "peer_witness"],
            service_endpoints={"witness": "http://test/witness"},
        )
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_resolve_verifier_node(self):
        snapshot = resolve_verifier_node(self.db)
        self.assertIsNotNone(snapshot)
        self.assertEqual(snapshot["entity_id"], LOCAL_VERIFIER_NODE_ID)
        self.assertEqual(snapshot["entity_type"], "verifier_node")
        self.assertIn("witness", snapshot["service_endpoints"])
        self.assertIn("proof_verify", snapshot["service_endpoints"])

    def test_network_manifest_sketch(self):
        manifest = build_verification_network_manifest(self.db)
        self.assertEqual(manifest["default_verifier_node_id"], LOCAL_VERIFIER_NODE_ID)
        self.assertEqual(manifest["verifier_node"]["entity_id"], LOCAL_VERIFIER_NODE_ID)
        self.assertIn("challenge", manifest["endpoints"]["contribution_challenge"])
        self.assertIn("proof_verify", manifest["endpoints"])

    def test_attach_verifier_node_to_consensus(self):
        consensus = {"passed": True, "avg_score": 0.8}
        snapshot = resolve_verifier_node(self.db)
        enriched = attach_verifier_node(consensus, snapshot)
        self.assertEqual(enriched["verifier_node_id"], LOCAL_VERIFIER_NODE_ID)
        self.assertEqual(enriched["verifier_node"]["entity_id"], LOCAL_VERIFIER_NODE_ID)

    def test_challenge_records_verifier_node_id(self):
        task = Task(title="Test", sponsor_id="human-1", status=TaskStatus.open)
        self.db.add(task)
        self.db.flush()
        contrib = ContributionEvent(
            task_id=task.id,
            primary_entity_id="human-1",
            contribution_type="knowledge",
            description="Test",
            status=ContributionStatus.approved,
        )
        self.db.add(contrib)
        self.db.flush()
        self.db.add(
            ContributionParticipant(
                contribution_id=contrib.id,
                entity_id="human-1",
                role=ParticipantRole.creator,
                weight=1.0,
            )
        )
        self.db.commit()

        challenge_contribution(
            self.db,
            contrib,
            challenger_entity_id="human-2",
            reason="Duplicate evidence suspected in bundle",
        )
        from models.ledger import LedgerRecord

        row = (
            self.db.query(LedgerRecord)
            .filter(LedgerRecord.event_type == "contribution_challenged")
            .order_by(LedgerRecord.created_at.desc())
            .first()
        )
        self.assertIsNotNone(row)
        self.assertEqual(row.payload.get("verifier_node_id"), LOCAL_VERIFIER_NODE_ID)


if __name__ == "__main__":
    unittest.main()
