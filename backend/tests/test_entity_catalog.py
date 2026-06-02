"""Platform entity catalog bootstrap tests."""

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import models  # noqa: F401
from database import Base
from genesis import DESUI_ID, LUMEN_0_ID, RAIN_ID, ensure_genesis_entities
from models.entity import Entity, EntityStatus, EntityType
from services.entity_catalog import (
    BOB_REVIEWER_NODE_ID,
    LOCAL_COMPUTE_NODE_ID,
    PROTOCOL_TREASURY_ID,
    RAIN_SPONSOR_ID,
    audit_entity_catalog,
    ensure_platform_entity_catalog,
)
from services.org_foundation import ensure_pocp_org_foundation


class EntityCatalogTests(unittest.TestCase):
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

    def test_ensure_registers_infrastructure_and_capabilities(self):
        result = ensure_platform_entity_catalog(self.db)
        self.db.commit()
        self.assertFalse(result["skipped"])
        self.assertIsNotNone(self.db.get(Entity, LOCAL_COMPUTE_NODE_ID))
        self.assertIsNotNone(self.db.get(Entity, PROTOCOL_TREASURY_ID))
        self.assertIsNotNone(self.db.get(Entity, RAIN_SPONSOR_ID))
        audit = audit_entity_catalog(self.db)
        self.assertNotIn("compute_node", audit["missing_types"])
        self.assertNotIn("verifier_node", audit["missing_types"])
        self.assertNotIn("reviewer_node", audit["missing_types"])
        self.assertNotIn("sponsor", audit["missing_types"])
        self.assertNotIn("protocol_treasury", audit["missing_types"])
        self.assertGreaterEqual(audit["capability_count"], 11)

    def test_idempotent_second_run(self):
        ensure_platform_entity_catalog(self.db)
        self.db.commit()
        first_audit = audit_entity_catalog(self.db)
        result = ensure_platform_entity_catalog(self.db)
        self.db.commit()
        self.assertEqual(result["infrastructure_created"], [])
        self.assertEqual(result["capabilities_created"], [])
        second_audit = audit_entity_catalog(self.db)
        self.assertEqual(first_audit["entity_count"], second_audit["entity_count"])
        self.assertEqual(first_audit["capability_count"], second_audit["capability_count"])

    def test_bob_reviewer_node_when_bob_exists(self):
        ensure_platform_entity_catalog(self.db)
        self.db.commit()
        self.assertIsNotNone(self.db.get(Entity, BOB_REVIEWER_NODE_ID))

    def test_lumen_capability_linked(self):
        ensure_platform_entity_catalog(self.db)
        self.db.commit()
        audit = audit_entity_catalog(self.db)
        self.assertNotIn("pocp-cap-lumen-reasoning", audit["missing_capabilities"])


if __name__ == "__main__":
    unittest.main()
