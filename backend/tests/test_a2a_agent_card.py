"""Tests for A2A Agent Card builder (BI-1)."""

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import models  # noqa: F401
from database import Base
from models.entity import Entity, EntityStatus, EntityType
from services.a2a_agent_card import (
    POCP_A2A_EXTENSION_URI,
    build_entity_agent_card,
    build_node_agent_card,
)
from services.compute_profile import register_compute_profile


class A2AAgentCardTests(unittest.TestCase):
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
        self.agent = Entity(
            entity_type=EntityType.agent,
            name="Study Bot",
            description="Research executor",
            status=EntityStatus.active,
            owner_id=None,
            metadata_={
                "capabilities": ["research", "summarize"],
                "tags": ["alpha"],
            },
        )
        self.db.add_all([self.human, self.agent])
        self.db.flush()
        self.agent.owner_id = self.human.id
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_build_entity_agent_card(self):
        card = build_entity_agent_card(self.db, self.agent.id)
        self.assertIsNotNone(card)
        self.assertEqual(card["name"], "Study Bot")
        self.assertIn("/entities/", card["url"])
        self.assertTrue(card["pocp"]["auto_finalization_enabled"])
        skill_ids = {s["id"] for s in card["skills"]}
        self.assertIn("study-agent-run", skill_ids)
        self.assertTrue(any(s["id"].startswith("declared-") for s in card["skills"]))
        ext_uris = [e["uri"] for e in card["capabilities"]["extensions"]]
        self.assertIn(POCP_A2A_EXTENSION_URI, ext_uris)

    def test_entity_card_includes_compute_offers(self):
        register_compute_profile(
            self.db,
            self.agent.id,
            {
                "offers": [{"capability": "witness", "adapters": ["mock"]}],
                "endpoints": {"base_url": "http://127.0.0.1:8000"},
            },
            owner_entity_id=self.human.id,
        )
        self.db.commit()
        card = build_entity_agent_card(self.db, self.agent.id)
        self.assertIsNotNone(card)
        self.assertIn("compute-witness", {s["id"] for s in card["skills"]})

    def test_missing_entity_returns_none(self):
        self.assertIsNone(build_entity_agent_card(self.db, "missing-id"))

    def test_build_node_agent_card(self):
        card = build_node_agent_card(self.db)
        self.assertEqual(card["name"], "PoCP AI Commons Node")
        self.assertIn("/api/v1/intelligence/a2a", card["url"])
        self.assertIn("intelligence-match", {s["id"] for s in card["skills"]})
        self.assertIn("bearerAuth", card["securitySchemes"])
        self.assertEqual(card["pocp"]["protocol_version"], "0.1")


if __name__ == "__main__":
    unittest.main()
