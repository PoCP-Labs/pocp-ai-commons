import unittest
from unittest.mock import MagicMock, patch

from tests.compute_test_db import make_compute_test_session
from services.compute_executor import complete_llm_job
from services.compute_jobs import clear_job_store


class ComputeExecutorTests(unittest.TestCase):
    def setUp(self):
        self.job_db = make_compute_test_session()
        clear_job_store(self.job_db)

    def tearDown(self):
        self.job_db.close()

    def test_complete_llm_job_updates_receipt(self):
        from services.compute_scheduler import ComputeJob, schedule_compute_job

        db = MagicMock()
        db.get.return_value = None
        db.query.return_value.filter.return_value.all.return_value = []
        db.add = self.job_db.add
        db.flush = self.job_db.flush

        with patch("services.compute_scheduler._local_node_candidate") as mock_local:
            mock_local.return_value = MagicMock(
                source="local_node",
                provider_entity_id=None,
                provider_node_id="node-local",
                base_url="http://localhost:8000",
                trust_weight=1.0,
                adapter="mock",
                model="mock",
                region="",
                rank_score=1.0,
                metadata={},
            )
            scheduled = schedule_compute_job(
                db,
                ComputeJob(capability="llm_inference", initiator_entity_id="human-1"),
            )
            self.job_db.commit()

        job_id = scheduled["job_id"]
        receipt = complete_llm_job(
            self.job_db,
            job_id,
            provider="mock",
            model="mock",
            prompt="hello",
            output="world",
            started_ms=0,
        )
        self.assertIsNotNone(receipt)
        self.assertEqual(receipt["capability"], "llm_inference")
        self.assertTrue(receipt["output_hash"])


if __name__ == "__main__":
    unittest.main()
