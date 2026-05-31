"""Tests for capability import (AgentSkills, catalog, bundled sync)."""

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models.entity import Entity, EntityStatus, EntityType
from services.capability_import import (
    import_skill_from_skill_md,
    list_capability_catalog,
    parse_skill_md,
    sync_bundled_capabilities,
)

SAMPLE_SKILL = """---
name: demo-skill
description: Demo skill for tests.
metadata:
  openclaw:
    category: test
---

# Demo

Do the thing.
"""


class CapabilityImportTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        org = Entity(
            entity_type=EntityType.organization,
            name="PoCP AI Commons",
            status=EntityStatus.active,
        )
        human = Entity(
            entity_type=EntityType.human,
            name="Maintainer",
            status=EntityStatus.active,
        )
        self.db.add_all([org, human])
        self.db.commit()
        self.maintainer_id = human.id

    def tearDown(self):
        self.db.close()

    def test_parse_skill_md(self):
        parsed = parse_skill_md(SAMPLE_SKILL)
        self.assertEqual(parsed["name"], "demo-skill")
        self.assertIn("Do the thing", parsed["instructions"])
        self.assertEqual(len(parsed["content_hash"]), 64)

    def test_import_idempotent(self):
        first = import_skill_from_skill_md(
            self.db,
            source="agentskills",
            skill_md=SAMPLE_SKILL,
            maintainer_id=self.maintainer_id,
            activate=True,
        )
        second = import_skill_from_skill_md(
            self.db,
            source="agentskills",
            skill_md=SAMPLE_SKILL,
            maintainer_id=self.maintainer_id,
            activate=True,
        )
        self.assertTrue(first["created"])
        self.assertFalse(second["created"])
        self.assertEqual(first["entity_id"], second["entity_id"])

    def test_catalog_lists_imported_skill(self):
        import_skill_from_skill_md(
            self.db,
            source="openclaw",
            skill_md=SAMPLE_SKILL,
            external_id="demo-skill",
            maintainer_id=self.maintainer_id,
            activate=False,
        )
        items = list_capability_catalog(self.db, source="openclaw")
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["status"], "pending")

    def test_sync_bundled(self):
        results = sync_bundled_capabilities(self.db)
        self.assertGreaterEqual(len(results), 2)
        slugs = {r["capability_source_key"] for r in results}
        self.assertIn("openclaw:summarize", slugs)
        self.assertIn("openclaw:study-notes", slugs)
        items = list_capability_catalog(self.db, source="openclaw")
        self.assertTrue(all(i["status"] == "active" for i in items))


if __name__ == "__main__":
    unittest.main()
