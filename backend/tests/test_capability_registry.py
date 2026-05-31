"""Neural Commons v0.4 — capability registry tests."""

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import models  # noqa: F401
from database import Base
from models.entity import Entity, EntityStatus, EntityType
from services.capability.registry import (
    descriptor_from_record,
    get_capability,
    register_capability,
    search_capabilities,
)
from services.entity_register import register_compute_node, register_protocol_treasury


class CapabilityRegistryTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        self.human = Entity(
            entity_type=EntityType.human,
            name="Alice",
            status=EntityStatus.active,
        )
        self.db.add(self.human)
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_register_and_search_capability(self):
        node = register_compute_node(
            self.db,
            name="GPU-1",
            description="Local inference",
            maintainer_id=self.human.id,
            region="lab-a",
            capabilities=["gpu_inference"],
        )
        record = register_capability(
            self.db,
            entity_id=node.id,
            capability_type="gpu_inference",
            name="Llama inference",
            unit="gpu_second",
            base_price=2.5,
            accepted_units=["AIC", "CC"],
        )
        self.db.commit()

        found = get_capability(self.db, record.id)
        self.assertIsNotNone(found)
        desc = descriptor_from_record(found)
        self.assertEqual(desc.capability_type, "gpu_inference")
        self.assertEqual(desc.accepted_units, ["AIC", "CC"])

        rows = search_capabilities(self.db, capability_type="gpu_inference", entity_id=node.id)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].name, "Llama inference")

    def test_register_rejects_unknown_entity(self):
        with self.assertRaises(ValueError):
            register_capability(
                self.db,
                entity_id="missing",
                capability_type="review",
                name="Review",
                unit="task",
            )

    def test_register_rejects_invalid_accepted_units(self):
        with self.assertRaises(ValueError):
            register_capability(
                self.db,
                entity_id=self.human.id,
                capability_type="review",
                name="Review",
                unit="task",
                accepted_units=["USD"],
            )

    def test_protocol_treasury_entity_type(self):
        treasury = register_protocol_treasury(
            self.db,
            governance_entity_id=self.human.id,
        )
        self.assertEqual(treasury.entity_type, EntityType.protocol_treasury)
        self.assertEqual(treasury.metadata_.get("treasury_policy"), "protocol_reserve")


if __name__ == "__main__":
    unittest.main()
