"""Node manifest API — entity facets and provider directory."""

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models.capability import (
    CapabilityAvailability,
    CapabilityType,
    CapabilityUnit,
    EntityCapability,
    PriceModel,
)
from models.entity import Entity, EntityStatus, EntityType
from models.wallet import Wallet
from services.compute_profile import register_compute_profile
from services.node_manifest import (
    build_entity_node_manifest,
    build_instance_node_manifest,
    list_provider_directory,
)


class NodeManifestTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        self.human = Entity(
            id="human-1",
            entity_type=EntityType.human,
            name="Alice",
            status=EntityStatus.active,
        )
        self.llm = Entity(
            id="llm-1",
            entity_type=EntityType.llm,
            name="Local LLM",
            status=EntityStatus.active,
        )
        self.db.add_all([self.human, self.llm])
        self.db.add(Wallet(entity_id="human-1", ai_credits=50, cp_balance=0))
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_consumer_only_manifest(self):
        manifest = build_entity_node_manifest(self.db, "human-1")
        self.assertEqual(manifest["protocol"], "pocp-node-manifest-v0.2-capability-first")
        self.assertIn("consumer", manifest["facets"])
        self.assertEqual(manifest["entity_id"], "human-1")

    def test_capability_provider_manifest(self):
        self.db.add(
            EntityCapability(
                entity_id="human-1",
                capability_type=CapabilityType.coding,
                name="Code Review",
                unit=CapabilityUnit.skill_invocation,
                price_model=PriceModel.fixed,
                base_price=8.0,
                accepted_units=["AIC"],
                verification_method="human_review",
                availability=CapabilityAvailability.available,
            )
        )
        self.db.commit()
        manifest = build_entity_node_manifest(self.db, "human-1")
        self.assertIn("capability_provider", manifest["facets"])
        self.assertEqual(len(manifest["capabilities"]), 1)
        self.assertEqual(manifest["capabilities"][0]["exchange_kind"], "capability")

    def test_compute_provider_manifest(self):
        register_compute_profile(
            self.db,
            "llm-1",
            {
                "offers": [{"capability": "llm_inference", "adapters": ["mock"]}],
                "endpoints": {"base_url": "http://127.0.0.1:8000"},
                "policy": {"accepts_public_jobs": True, "visibility": "public"},
                "status": "active",
            },
        )
        self.db.commit()
        manifest = build_entity_node_manifest(self.db, "llm-1")
        self.assertIn("compute_provider", manifest["facets"])
        self.assertTrue(any(c["exchange_kind"] == "compute" for c in manifest["capabilities"]))

    def test_provider_directory_lists_registry_and_compute(self):
        self.db.add(
            EntityCapability(
                entity_id="human-1",
                capability_type=CapabilityType.reasoning,
                name="Tutor",
                unit=CapabilityUnit.skill_invocation,
                price_model=PriceModel.fixed,
                base_price=5.0,
                accepted_units=["AIC"],
                verification_method="policy_delegate",
                availability=CapabilityAvailability.available,
            )
        )
        register_compute_profile(
            self.db,
            "llm-1",
            {
                "offers": [{"capability": "llm_inference", "adapters": ["mock"]}],
                "endpoints": {"base_url": "http://127.0.0.1:8000"},
                "policy": {"accepts_public_jobs": True, "visibility": "public"},
                "status": "active",
            },
        )
        self.db.commit()

        directory = list_provider_directory(self.db)
        self.assertGreaterEqual(directory["count"], 2)
        kinds = {item["exchange_kind"] for item in directory["items"]}
        self.assertIn("capability", kinds)
        self.assertIn("compute", kinds)

        compute_only = list_provider_directory(self.db, exchange_kind="compute")
        self.assertTrue(all(i["exchange_kind"] == "compute" for i in compute_only["items"]))

    def test_instance_manifest(self):
        manifest = build_instance_node_manifest(self.db)
        self.assertEqual(manifest["kind"], "instance")
        self.assertIn("capabilities_directory", manifest["endpoints"])


if __name__ == "__main__":
    unittest.main()
