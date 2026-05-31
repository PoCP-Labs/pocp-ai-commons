import unittest
from unittest.mock import MagicMock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import models  # noqa: F401
from database import Base
from services.compute_jobs import clear_job_store, get_job_record
from services.compute_profile import validate_compute_profile, entity_offers_capability
from services.compute_receipt import build_compute_receipt, verify_compute_receipt
from services.compute_scheduler import ComputeJob, list_compute_candidates, select_compute_provider
from models.entity import Entity, EntityStatus, EntityType


class ComputeProfileTests(unittest.TestCase):
    def test_validate_compute_profile(self):
        profile = validate_compute_profile(
            {
                "offers": [{"capability": "witness", "adapters": ["ollama"]}],
                "endpoints": {"base_url": "http://lab.example:8100"},
            }
        )
        self.assertEqual(profile["spec_version"], "0.1")
        self.assertEqual(profile["offers"][0]["capability"], "witness")

    def test_invalid_capability_raises(self):
        with self.assertRaises(ValueError):
            validate_compute_profile({"offers": [{"capability": "quantum_flux"}]})

    def test_entity_offers_capability(self):
        entity = MagicMock()
        entity.metadata_ = {
            "compute_profile": {
                "status": "active",
                "offers": [{"capability": "llm_inference", "models": ["qwen2.5:7b"]}],
            }
        }
        self.assertTrue(entity_offers_capability(entity, "llm_inference"))
        self.assertFalse(entity_offers_capability(entity, "mcp_host"))


class ComputeReceiptTests(unittest.TestCase):
    def test_receipt_hash_stable(self):
        r1 = build_compute_receipt(
            provider_entity_id="e1",
            provider_node_id="node-a",
            capability="witness",
            adapter="ollama",
            input_material="hello",
        )
        r2 = build_compute_receipt(
            provider_entity_id="e1",
            provider_node_id="node-a",
            capability="witness",
            adapter="ollama",
            input_material="hello",
            started_at=r1["started_at"],
            finished_at=r1["finished_at"],
        )
        self.assertEqual(r1["integrity"]["receipt_hash"], r2["integrity"]["receipt_hash"])
        self.assertTrue(verify_compute_receipt(r1))


class ComputeSchedulerTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.job_db = self.Session()
        clear_job_store(self.job_db)

    def tearDown(self):
        self.job_db.close()

    def test_select_local_node_when_no_entities(self):
        db = MagicMock()
        db.get.return_value = None
        db.query.return_value.filter.return_value.all.return_value = []

        job = ComputeJob(capability="witness", initiator_entity_id="human-1")
        with patch("services.compute_scheduler._local_node_candidate") as mock_local:
            mock_local.return_value = MagicMock(
                source="local_node",
                provider_entity_id=None,
                provider_node_id="local",
                base_url="http://localhost:8000",
                trust_weight=1.0,
                adapter="mock",
                model=None,
                region="",
                rank_score=0.0,
                metadata={},
            )
            selected = select_compute_provider(db, job)
            self.assertIsNotNone(selected)
            self.assertEqual(selected.source, "local_node")

    def test_schedule_job_creates_record(self):
        db = MagicMock()
        db.get.return_value = None
        db.query.return_value.filter.return_value.all.return_value = []
        db.add = self.job_db.add
        db.flush = self.job_db.flush

        job = ComputeJob(capability="witness", initiator_entity_id="human-1")
        with patch("services.compute_scheduler.select_compute_provider") as mock_select:
            mock_select.return_value = MagicMock(
                source="local_node",
                provider_entity_id="llm-1",
                provider_node_id="node-local",
                base_url="http://localhost:8000",
                trust_weight=1.0,
                adapter="mock",
                model="mock",
                region="",
                rank_score=1.0,
                metadata={},
            )
            from services.compute_scheduler import schedule_compute_job

            result = schedule_compute_job(db, job)
            self.job_db.commit()
            self.assertEqual(result["status"], "scheduled")
            self.assertIn("job_id", result)
            stored = get_job_record(self.job_db, result["job_id"])
            self.assertTrue(verify_compute_receipt(stored["compute_receipt"]))

    def test_entity_candidate_ranking_prefers_owner(self):
        initiator = Entity(
            id="human-1",
            entity_type=EntityType.human,
            name="Alice",
            status=EntityStatus.active,
        )
        owned = Entity(
            id="tool-1",
            entity_type=EntityType.tool,
            name="Lab GPU",
            status=EntityStatus.active,
            owner_id="human-1",
            metadata_={
                "compute_profile": {
                    "status": "active",
                    "offers": [{"capability": "witness", "adapters": ["ollama"]}],
                    "endpoints": {"base_url": "http://lab:8100"},
                    "accountability": {"owner_entity_id": "human-1"},
                }
            },
        )
        db = MagicMock()
        db.get.return_value = initiator
        db.query.return_value.filter.return_value.all.return_value = [owned]

        job = ComputeJob(capability="witness", initiator_entity_id="human-1")
        with patch("services.compute_scheduler._local_node_candidate", return_value=None):
            with patch("services.compute_scheduler._peer_candidates", return_value=[]):
                with patch(
                    "services.compute_scheduler.load_compute_provider_reputation_map",
                    return_value={},
                ):
                    candidates = list_compute_candidates(db, job)
                self.assertEqual(len(candidates), 1)
                self.assertEqual(candidates[0].provider_entity_id, "tool-1")
                self.assertGreater(candidates[0].rank_score, 1.0)


if __name__ == "__main__":
    unittest.main()
