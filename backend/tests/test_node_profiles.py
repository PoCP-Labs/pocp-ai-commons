"""PR-05 — NodeProfile persistence and discovery."""

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import models  # noqa: F401
from database import Base
from genesis import DESUI_ID, LUMEN_0_ID, RAIN_ID, ensure_genesis_entities
from models.entity import Entity, EntityStatus, EntityType
from models.node_profile import NodeProfileRecord
from services.capability.bootstrap import seed_platform_capabilities
from services.entity_catalog import ensure_platform_entity_catalog
from services.entity_register import register_compute_node
from services.node.store import (
    build_entity_node_manifest,
    discover_nodes,
    get_node_by_entity,
    register_node,
)


class NodeProfileTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        ensure_genesis_entities(self.db)
        rain = self.db.get(Entity, RAIN_ID)
        org = Entity(
            entity_type=EntityType.organization,
            name="PoCP AI Commons",
            status=EntityStatus.active,
            owner_id=rain.id,
            creator_id=rain.id,
        )
        self.db.add(org)
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_register_and_discover_compute_node(self):
        node_entity = register_compute_node(
            self.db,
            entity_id="pocp-entity-test-compute",
            name="Test Compute",
            description="test",
            maintainer_id=self.db.get(Entity, RAIN_ID).id,
        )
        self.db.commit()
        record = register_node(
            self.db,
            entity_id=node_entity.id,
            node_type="compute",
            base_url="https://compute.example.com",
            published_capabilities=["gpu_inference"],
        )
        self.db.commit()
        self.assertEqual(record.entity_id, node_entity.id)
        self.assertTrue(record.health_url.endswith("/pocp/health"))

        found = discover_nodes(self.db, capability_type="gpu_inference")
        self.assertTrue(any(r.id == record.id for r in found))

    def test_entity_manifest_includes_capabilities(self):
        result = ensure_platform_entity_catalog(self.db)
        self.db.commit()
        self.assertFalse(result["skipped"])
        manifest = build_entity_node_manifest(self.db, LUMEN_0_ID)
        self.assertIsNotNone(manifest)
        self.assertEqual(manifest["entity_id"], LUMEN_0_ID)

    def test_idempotent_register_same_entity(self):
        register_node(
            self.db,
            entity_id=DESUI_ID,
            node_type="verifier",
            base_url="http://localhost:8008",
        )
        self.db.commit()
        first = get_node_by_entity(self.db, DESUI_ID)
        register_node(
            self.db,
            entity_id=DESUI_ID,
            node_type="verifier",
            base_url="http://localhost:9000",
        )
        self.db.commit()
        second = get_node_by_entity(self.db, DESUI_ID)
        self.assertEqual(first.id, second.id)
        self.assertEqual(second.base_url, "http://localhost:9000")

    def test_catalog_creates_node_profiles(self):
        ensure_platform_entity_catalog(self.db)
        self.db.commit()
        count = self.db.query(NodeProfileRecord).count()
        self.assertGreaterEqual(count, 3)


if __name__ == "__main__":
    unittest.main()
