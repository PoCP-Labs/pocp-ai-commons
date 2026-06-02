"""PA-1 capability registry bootstrap — 11+ seeded capabilities."""

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import models  # noqa: F401
from database import Base
from genesis import DESUI_ID, LUMEN_0_ID, RAIN_ID, ensure_genesis_entities
from models.entity import Entity, EntityStatus, EntityType
from services.capability.bootstrap import audit_registry, seed_platform_capabilities
from services.capability.seeds import REGISTRY_MIN_COUNT, expected_capability_ids
from services.entity_catalog import ensure_platform_entity_catalog
from services.org_foundation import ensure_pocp_org_foundation


class CapabilityBootstrapTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        ensure_genesis_entities(self.db)
        rain = self.db.get(Entity, RAIN_ID)
        bob = Entity(entity_type=EntityType.human, name="Bob", status=EntityStatus.active, owner_id=rain.id)
        org = Entity(
            entity_type=EntityType.organization,
            name="PoCP AI Commons",
            status=EntityStatus.active,
            owner_id=rain.id,
            creator_id=rain.id,
        )
        skill = Entity(
            entity_type=EntityType.skill,
            name="R-Tutor Skill",
            status=EntityStatus.active,
            owner_id=rain.id,
            creator_id=rain.id,
        )
        self.db.add_all([bob, org, skill])
        self.db.commit()
        ensure_pocp_org_foundation(self.db)
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_seed_platform_capabilities_meets_minimum(self):
        ensure_platform_entity_catalog(self.db)
        self.db.commit()
        audit = audit_registry(self.db)
        self.assertGreaterEqual(audit["capability_count"], REGISTRY_MIN_COUNT)
        self.assertTrue(audit["registry_complete"])
        self.assertEqual(len(expected_capability_ids()), REGISTRY_MIN_COUNT)

    def test_seed_registers_genesis_capabilities(self):
        seed_platform_capabilities(
            self.db, rain_id=RAIN_ID, maintainer_id=self.db.get(Entity, RAIN_ID).id
        )
        self.db.commit()
        audit = audit_registry(self.db)
        self.assertGreaterEqual(audit["capability_count"], 4)
        self.assertNotIn("pocp-cap-lumen-reasoning", audit["missing_capabilities"])
        self.assertIsNotNone(self.db.get(Entity, LUMEN_0_ID))
        self.assertIsNotNone(self.db.get(Entity, DESUI_ID))


if __name__ == "__main__":
    unittest.main()
