"""Tests for external compute adapters (Akash / Render stubs)."""

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from genesis import RAIN_ID
from models.entity import Entity, EntityStatus, EntityType
from services.compute_adapters.base import AdapterJobSpec
from services.compute_adapters.base import AdapterJobSpec
from services.compute_adapters.registry import get_adapter, list_adapters
from services.compute_adapters.service import import_adapter_provider, poll_adapter_job, submit_adapter_job
from services.compute_adapters.stub_state import reset_stub_jobs
from services.compute_jobs import clear_job_store
from services.compute_receipt import verify_compute_receipt


class ComputeAdapterTests(unittest.TestCase):
    def setUp(self):
        reset_stub_jobs()
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

    def test_list_adapters_includes_akash_and_render(self):
        slugs = {item["slug"] for item in list_adapters()}
        self.assertIn("akash", slugs)
        self.assertIn("render-network", slugs)
        self.assertIn("io-net", slugs)
        self.assertIn("gensyn", slugs)

    def test_gensyn_training_stub_complete(self):
        imported = import_adapter_provider(
            self.db,
            "gensyn",
            {
                "display_name": "Gensyn Stub Trainer",
                "offers": [{"capability": "training", "adapters": ["gensyn"]}],
            },
            owner_entity_id=RAIN_ID,
        )
        provider_id = imported["entity_id"]
        job = submit_adapter_job(
            self.db,
            "gensyn",
            capability="training",
            requester_entity_id=RAIN_ID,
            provider_entity_id=provider_id,
            task_id="task-gensyn-1",
            constraints={"objective": "fine_tune_demo", "epochs": 2},
        )
        poll_adapter_job(self.db, "gensyn", job["job_id"])
        poll_adapter_job(self.db, "gensyn", job["job_id"])
        done = poll_adapter_job(self.db, "gensyn", job["job_id"])
        self.assertEqual(done["status"], "completed")
        receipt = done["compute_receipt"]
        self.assertEqual(receipt.get("capability"), "training")
        self.assertEqual(receipt.get("adapter"), "gensyn")
        self.assertIn("training_attestation", receipt.get("integrity") or {})

    def test_gensyn_rejects_non_training_capability(self):
        adapter = get_adapter("gensyn")
        spec = AdapterJobSpec(
            capability="llm_inference",
            requester_entity_id=RAIN_ID,
            provider_entity_id="p1",
            task_id="t1",
        )
        with self.assertRaises(ValueError):
            adapter.submit_job(spec)

    def test_job_spec_requires_contribution_binding(self):
        spec = AdapterJobSpec(
            capability="llm_inference",
            requester_entity_id=RAIN_ID,
            provider_entity_id="gpu-1",
        )
        with self.assertRaises(ValueError):
            spec.validate()

    def test_import_akash_provider(self):
        result = import_adapter_provider(
            self.db,
            "akash",
            {
                "display_name": "Akash Demo GPU",
                "external_provider_id": "dseq-demo-1",
                "offers": [{"capability": "llm_inference", "adapters": ["akash"], "models": ["llama3"]}],
            },
            owner_entity_id=RAIN_ID,
        )
        self.db.commit()
        self.assertTrue(result["entity_id"].startswith("pocp-adapt-"))
        profile = result["compute_profile"]
        self.assertEqual(profile["offers"][0]["adapters"][0], "akash")

    def test_akash_stub_submit_poll_complete(self):
        imported = import_adapter_provider(
            self.db,
            "akash",
            {"display_name": "Akash Stub Node"},
            owner_entity_id=RAIN_ID,
        )
        provider_id = imported["entity_id"]

        job = submit_adapter_job(
            self.db,
            "akash",
            capability="llm_inference",
            requester_entity_id=RAIN_ID,
            provider_entity_id=provider_id,
            task_id="task-adapter-demo",
            constraints={"input_preview": "hello adapter"},
        )
        self.assertEqual(job["status"], "scheduled")
        self.assertIn("external_job_id", (job.get("execution") or {}))

        running = poll_adapter_job(self.db, "akash", job["job_id"])
        self.assertEqual(running["status"], "scheduled")

        done = poll_adapter_job(self.db, "akash", job["job_id"])
        self.assertEqual(done["status"], "completed")
        receipt = done.get("compute_receipt") or {}
        self.assertEqual(receipt.get("adapter"), "akash")
        self.assertTrue(verify_compute_receipt(receipt))
        extra = receipt.get("extra") or {}
        self.assertEqual(extra.get("network"), "akash")

    def test_unknown_adapter_raises(self):
        with self.assertRaises(ValueError):
            get_adapter("not-a-network")


if __name__ == "__main__":
    unittest.main()
