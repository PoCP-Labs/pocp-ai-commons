"""Phase γ — compute provider reputation, matching, scheduler weighting."""

import unittest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models.entity import Entity, EntityStatus, EntityType
from models.reputation_audit import ReputationAuditEntry
from models.wallet import Wallet
from services.compute_matching import infer_required_capabilities, recommend_compute_providers
from services.compute_receipt import build_compute_receipt
from services.compute_reputation import (
    COMPUTE_PROVIDER_CATEGORY,
    grant_compute_provider_reputation,
    load_compute_provider_reputation_map,
)
from services.compute_scheduler import ComputeJob, list_compute_candidates
from services.compute_settlement import settle_compute_provider


class ComputeReputationTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        self.db.add(
            Entity(
                id="llm-1",
                entity_type=EntityType.llm,
                name="Lumen-0",
                status=EntityStatus.active,
            )
        )
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_grant_reputation_idempotent(self):
        receipt = build_compute_receipt(
            provider_entity_id="llm-1",
            provider_node_id="node-a",
            capability="witness",
            adapter="mock",
            contribution_id="c1",
            input_material="in",
            output_material="out",
        )
        first = grant_compute_provider_reputation(self.db, receipt, consumer_entity_id="human-1")
        self.db.commit()
        self.assertTrue(first["granted"])
        self.assertEqual(first["category"], COMPUTE_PROVIDER_CATEGORY)

        second = grant_compute_provider_reputation(self.db, receipt, consumer_entity_id="human-1")
        self.assertFalse(second["granted"])

        audits = self.db.query(ReputationAuditEntry).filter(ReputationAuditEntry.entity_id == "llm-1").all()
        self.assertEqual(len(audits), 1)


class ComputeSettlementGammaTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        self.db.add(
            Entity(
                id="llm-1",
                entity_type=EntityType.llm,
                name="Lumen-0",
                status=EntityStatus.active,
            )
        )
        self.db.add(Wallet(entity_id="llm-1", cp_balance=0, ai_credits=10))
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_settlement_grants_reputation_and_ledger(self):
        receipt = build_compute_receipt(
            provider_entity_id="llm-1",
            provider_node_id="node-a",
            capability="llm_inference",
            adapter="mock",
            contribution_id="c1",
            input_material="in",
            output_material="out",
        )
        result = settle_compute_provider(self.db, receipt, consumer_entity_id="human-1")
        self.db.commit()
        self.assertTrue(result["settled"])
        self.assertTrue(result["reputation"]["granted"])

        rep_map = load_compute_provider_reputation_map(self.db)
        self.assertGreater(rep_map.get("llm-1", 0), 0)


class ComputeMatchingTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        entity = Entity(
            entity_type=EntityType.llm,
            name="Rain GPU",
            status=EntityStatus.active,
            metadata_={
                "compute_profile": {
                    "spec_version": "0.1",
                    "status": "active",
                    "offers": [{"capability": "llm_inference", "models": ["qwen2.5:7b"], "adapters": ["ollama"]}],
                    "endpoints": {"base_url": "http://127.0.0.1:11434"},
                    "capacity": {"region": "lab"},
                    "accountability": {"owner_entity_id": "human-rain"},
                    "policy": {},
                }
            },
        )
        self.db.add(entity)
        self.db.commit()
        self.provider_id = entity.id

    def tearDown(self):
        self.db.close()

    def test_infer_capabilities_for_research_task(self):
        caps = infer_required_capabilities(
            task_keywords={"research", "paper", "matrix"},
            contribution_type="research_note",
        )
        capability_names = [item["capability"] for item in caps]
        self.assertIn("llm_inference", capability_names)

    def test_recommend_providers(self):
        match = recommend_compute_providers(
            self.db,
            contribution_type="research_note",
            task_id=None,
            limit_per_capability=2,
        )
        self.assertGreaterEqual(len(match["recommended_compute_providers"]), 1)
        top = match["recommended_compute_providers"][0]
        self.assertEqual(top["entity_id"], self.provider_id)


class ComputeSchedulerReputationTests(unittest.TestCase):
    def test_reputation_boosts_entity_rank(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        db = sessionmaker(bind=engine)()

        low = Entity(
            id="low-rep",
            entity_type=EntityType.llm,
            name="Low Rep",
            status=EntityStatus.active,
            metadata_={
                "compute_profile": {
                    "spec_version": "0.1",
                    "status": "active",
                    "offers": [{"capability": "witness", "adapters": ["mock"]}],
                    "endpoints": {},
                    "capacity": {},
                    "accountability": {},
                    "policy": {},
                }
            },
        )
        high = Entity(
            id="high-rep",
            entity_type=EntityType.llm,
            name="High Rep",
            status=EntityStatus.active,
            metadata_={
                "compute_profile": {
                    "spec_version": "0.1",
                    "status": "active",
                    "offers": [{"capability": "witness", "adapters": ["mock"]}],
                    "endpoints": {},
                    "capacity": {},
                    "accountability": {},
                    "policy": {},
                }
            },
        )
        db.add_all([low, high])
        db.commit()

        with patch("services.compute_scheduler.load_compute_provider_reputation_map") as mock_rep:
            mock_rep.return_value = {"low-rep": 0.0, "high-rep": 10.0}
            with patch("services.compute_scheduler._local_node_candidate", return_value=None):
                candidates = list_compute_candidates(
                    db,
                    ComputeJob(capability="witness", initiator_entity_id=None),
                )

        entity_candidates = [c for c in candidates if c.source == "entity"]
        self.assertEqual(len(entity_candidates), 2)
        self.assertEqual(entity_candidates[0].provider_entity_id, "high-rep")
        db.close()


if __name__ == "__main__":
    unittest.main()
