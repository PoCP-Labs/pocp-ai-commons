"""Tests for demo compute profile seeding."""

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from genesis import DESUI_ID, LUMEN_0_ID, RAIN_ID
from models.entity import Entity, EntityStatus, EntityType
from services.compute_profile import get_compute_profile
from services.compute_seed import ensure_demo_compute_profiles, R_DOCS_TOOL_ID


class ComputeSeedTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()

        self.rain = Entity(id=RAIN_ID, entity_type=EntityType.human, name="Rain", status=EntityStatus.active)
        self.lumen = Entity(id=LUMEN_0_ID, entity_type=EntityType.llm, name="Lumen-0", status=EntityStatus.active)
        self.desui = Entity(id=DESUI_ID, entity_type=EntityType.llm, name="DeSui", status=EntityStatus.active)
        self.tool = Entity(
            id=R_DOCS_TOOL_ID,
            entity_type=EntityType.tool,
            name="R Docs MCP Tool",
            owner_id=RAIN_ID,
            status=EntityStatus.active,
        )
        self.db.add_all([self.rain, self.lumen, self.desui, self.tool])
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_ensure_demo_compute_profiles_idempotent(self):
        first = ensure_demo_compute_profiles(
            self.db, rain=self.rain, lumen=self.lumen, desui=self.desui, tool=self.tool
        )
        self.db.commit()
        self.assertGreaterEqual(first, 3)

        second = ensure_demo_compute_profiles(
            self.db, rain=self.rain, lumen=self.lumen, desui=self.desui, tool=self.tool
        )
        self.assertEqual(second, 0)

        lumen_profile = get_compute_profile(self.db.get(Entity, LUMEN_0_ID))
        self.assertIsNotNone(lumen_profile)
        self.assertTrue(any(o["capability"] == "witness" for o in lumen_profile["offers"]))


if __name__ == "__main__":
    unittest.main()
