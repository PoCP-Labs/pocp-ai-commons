"""Tests for Entity ontology validation and typed registration."""

import unittest
from unittest.mock import MagicMock

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from intelligence.entity_ontology import (
    enrich_entity_record,
    ontology_document,
    role_fits_entity_type,
    validate_entity_type,
    validate_participant_role,
)
from models.entity import Entity, EntityStatus, EntityType
from services.entity_register import (
    register_dataset,
    register_entity,
    register_tool,
    validate_participants_for_submission,
)


class EntityOntologyTests(unittest.TestCase):
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

    def test_ontology_document_has_nine_types(self):
        doc = ontology_document()
        self.assertEqual(doc["spec_version"], "0.1")
        self.assertEqual(len(doc["entity_types"]), 9)
        self.assertIn("witness", doc["participant_roles"])
        self.assertEqual(doc["docs"], "docs/ENTITY-ONTOLOGY.md")

    def test_validate_entity_type_rejects_unknown(self):
        with self.assertRaises(ValueError):
            validate_entity_type("spaceship")

    def test_validate_participant_role_rejects_unknown(self):
        with self.assertRaises(ValueError):
            validate_participant_role("janitor")

    def test_role_fits_entity_type(self):
        self.assertTrue(role_fits_entity_type("verifier", "llm"))
        self.assertTrue(role_fits_entity_type("reviewer", "human"))
        self.assertTrue(role_fits_entity_type("reviewer", "agent"))
        self.assertTrue(role_fits_entity_type("reviewer", "llm"))
        self.assertFalse(role_fits_entity_type("skill_provider", "agent"))

    def test_register_tool_entity(self):
        tool = register_tool(
            self.db,
            name="Git MCP",
            description="Git operations",
            maintainer_id=self.human.id,
            tool_kind="mcp",
            mcp_server="git",
        )
        self.db.commit()
        self.assertEqual(tool.entity_type, EntityType.tool)
        self.assertEqual(tool.owner_id, self.human.id)
        self.assertEqual(tool.metadata_["tool_kind"], "mcp")

    def test_register_tool_with_stable_id(self):
        tool = register_tool(
            self.db,
            entity_id="pocp-test-tool",
            name="Calc",
            description="Calculator",
            maintainer_id=self.human.id,
        )
        self.db.commit()
        self.assertEqual(tool.id, "pocp-test-tool")

    def test_register_dataset_entity(self):
        ds = register_dataset(
            self.db,
            name="R cheatsheet",
            description="Sample dataset",
            maintainer_id=self.human.id,
            source_uri="https://example.com/r.csv",
            license="CC-BY",
        )
        self.db.commit()
        self.assertEqual(ds.entity_type, EntityType.dataset)
        self.assertEqual(ds.metadata_["license"], "CC-BY")

    def test_register_entity_rejects_bad_type(self):
        with self.assertRaises(ValueError):
            register_entity(
                self.db,
                entity_type="invalid",
                name="Bad",
                description=None,
                owner_id=self.human.id,
                creator_id=self.human.id,
            )

    def test_validate_participants_for_submission(self):
        llm = Entity(
            entity_type=EntityType.llm,
            name="Lumen-0",
            owner_id=self.human.id,
            status=EntityStatus.active,
        )
        self.db.add(llm)
        self.db.commit()
        entities = {self.human.id: self.human, llm.id: llm}
        validate_participants_for_submission(
            [
                {"entity_id": self.human.id, "role": "creator"},
                {"entity_id": llm.id, "role": "verifier"},
            ],
            entities,
        )
        validate_participants_for_submission(
            [{"entity_id": llm.id, "role": "reviewer"}],
            entities,
        )

    def test_agent_reviewer_allowed(self):
        agent = Entity(
            entity_type=EntityType.agent,
            name="Clarion-0",
            status=EntityStatus.active,
        )
        self.db.add(agent)
        self.db.commit()
        validate_participants_for_submission(
            [{"entity_id": agent.id, "role": "reviewer"}],
            {agent.id: agent},
        )

    def test_enrich_entity_record(self):
        enriched = enrich_entity_record(self.human)
        self.assertEqual(enriched["entity_type"], "human")
        self.assertTrue(enriched["ontology"]["accountable_principal"])
        self.assertIn("creator", enriched["ontology"]["typical_roles"])


if __name__ == "__main__":
    unittest.main()
