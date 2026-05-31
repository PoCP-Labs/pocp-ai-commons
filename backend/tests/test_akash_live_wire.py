"""Akash live wire client tests."""

import os
import unittest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from genesis import RAIN_ID
from models.entity import Entity, EntityStatus, EntityType
from services.compute_adapters.akash import AkashComputeAdapter
from services.compute_adapters.base import AdapterJobSpec
from services.compute_adapters.service import import_adapter_provider, poll_adapter_job, submit_adapter_job
from services.compute_adapters.stub_state import reset_stub_jobs
from services.compute_jobs import clear_job_store


class AkashLiveWireTests(unittest.TestCase):
    def setUp(self):
        reset_stub_jobs()
        self._env_backup = {
            "POCP_AKASH_API_URL": os.environ.get("POCP_AKASH_API_URL"),
            "POCP_AKASH_API_TOKEN": os.environ.get("POCP_AKASH_API_TOKEN"),
            "POCP_ADAPTER_LIVE_ENABLED": os.environ.get("POCP_ADAPTER_LIVE_ENABLED"),
        }
        os.environ["POCP_AKASH_API_URL"] = "https://akash-gateway.test/"
        os.environ["POCP_ADAPTER_LIVE_ENABLED"] = "true"
        os.environ.pop("POCP_AKASH_API_TOKEN", None)

        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        clear_job_store(self.db)
        self.rain = Entity(
            id=RAIN_ID,
            entity_type=EntityType.human,
            name="Rain",
            status=EntityStatus.active,
        )
        self.db.add(self.rain)
        self.db.commit()

    def tearDown(self):
        self.db.close()
        reset_stub_jobs()
        for key, value in self._env_backup.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def test_adapter_effective_mode_live(self):
        adapter = AkashComputeAdapter()
        self.assertEqual(adapter.effective_mode(), "live")

    @patch("services.compute_adapters.akash_live.request_json")
    def test_live_submit_and_poll_complete(self, mock_request):
        mock_request.side_effect = [
            {"deployment_id": "dseq-live-99", "status": "pending"},
            {"status": "activating"},
            {"status": "active", "gpu_seconds": 18.0, "output_preview": "live inference ok"},
        ]

        imported = import_adapter_provider(
            self.db,
            "akash",
            {"display_name": "Akash Live Node"},
            owner_entity_id=RAIN_ID,
        )
        job = submit_adapter_job(
            self.db,
            "akash",
            capability="llm_inference",
            requester_entity_id=RAIN_ID,
            provider_entity_id=imported["entity_id"],
            contribution_id="contrib-live-1",
            constraints={"image": "ghcr.io/demo/infer:latest"},
        )
        self.assertEqual(job["selected_provider"]["mode"], "live")
        self.assertEqual(job["execution"]["external_job_id"], "dseq-live-99")

        poll_adapter_job(self.db, "akash", job["job_id"])
        done = poll_adapter_job(self.db, "akash", job["job_id"])
        self.assertEqual(done["status"], "completed")
        receipt = done["compute_receipt"]
        self.assertEqual(receipt["adapter"], "akash")
        self.assertEqual(receipt["extra"]["adapter_mode"], "live")
        self.assertEqual(receipt["extra"]["deployment_mode"], "live")
        self.assertEqual(receipt["extra"]["resource_units"]["gpu_seconds"], 18.0)

        self.assertEqual(mock_request.call_count, 3)
        first_call = mock_request.call_args_list[0]
        self.assertEqual(first_call[0][0], "POST")
        self.assertIn("/v1/deployments", first_call[0][1])

    @patch("services.compute_adapters.akash_live.request_json")
    def test_live_poll_failure(self, mock_request):
        mock_request.side_effect = [
            {"deployment_id": "dseq-fail", "status": "pending"},
            {"status": "failed", "error": "lease rejected"},
        ]
        spec = AdapterJobSpec(
            capability="llm_inference",
            requester_entity_id=RAIN_ID,
            provider_entity_id="p1",
            task_id="t-fail",
        )
        adapter = AkashComputeAdapter()
        submit = adapter.submit_job(spec)
        poll = adapter.poll_job(submit.external_job_id)
        self.assertEqual(poll.status.value, "failed")


if __name__ == "__main__":
    unittest.main()
