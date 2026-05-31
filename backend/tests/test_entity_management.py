"""Entity list filters and owner-scoped PATCH rules."""

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models.entity import Entity, EntityStatus, EntityType
from models.organization import Organization
from services.entity_management import (
    apply_entity_patch,
    assert_entity_governable_by_actor,
    list_pending_for_actor,
    query_entities,
    review_entity,
)


class EntityManagementTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine)()

    def tearDown(self):
        self.db.close()

    def test_query_entities_filter_type(self):
        human = Entity(entity_type=EntityType.human, name="FilterHuman", status=EntityStatus.active)
        llm = Entity(
            id="pocp-entity-lumen-0",
            entity_type=EntityType.llm,
            name="Lumen-0",
            status=EntityStatus.active,
        )
        self.db.add_all([human, llm])
        self.db.commit()

        all_llms = query_entities(self.db, entity_type="llm")
        self.assertEqual(len(all_llms), 1)
        self.assertEqual(all_llms[0].name, "Lumen-0")

        genesis = query_entities(self.db, genesis_only=True)
        self.assertTrue(any(e.id == "pocp-entity-lumen-0" for e in genesis))

    def test_genesis_entity_not_mutable_by_owner(self):
        owner = Entity(entity_type=EntityType.human, name="Owner", status=EntityStatus.active)
        genesis = Entity(
            id="pocp-entity-desui",
            entity_type=EntityType.llm,
            name="DeSui",
            status=EntityStatus.active,
        )
        self.db.add_all([owner, genesis])
        self.db.flush()

        with self.assertRaises(ValueError) as ctx:
            assert_entity_governable_by_actor(self.db, genesis, owner.id)
        self.assertIn("Genesis", str(ctx.exception))

    def test_owner_can_patch_description(self):
        owner = Entity(entity_type=EntityType.human, name="Owner", status=EntityStatus.active)
        skill = Entity(
            entity_type=EntityType.skill,
            name="My Skill",
            owner_id=owner.id,
            creator_id=owner.id,
            status=EntityStatus.active,
            metadata_={},
        )
        self.db.add(owner)
        self.db.flush()
        skill.owner_id = owner.id
        skill.creator_id = owner.id
        self.db.add(skill)
        self.db.flush()

        assert_entity_governable_by_actor(self.db, skill, owner.id)
        apply_entity_patch(
            skill,
            name=None,
            description="Updated",
            status="inactive",
            metadata={"version": "2"},
        )
        self.assertEqual(skill.description, "Updated")
        self.assertEqual(skill.status, EntityStatus.inactive)
        self.assertEqual(skill.metadata_["version"], "2")

    def test_org_proxy_can_approve_pending_skill(self):
        proxy = Entity(entity_type=EntityType.human, name="Bob", status=EntityStatus.active)
        org_entity = Entity(
            entity_type=EntityType.organization,
            name="PoCP AI Commons",
            status=EntityStatus.active,
        )
        self.db.add(proxy)
        self.db.flush()
        org_entity.owner_id = proxy.id
        self.db.add(org_entity)
        self.db.flush()
        self.db.add(
            Organization(
                entity_id=org_entity.id,
                org_type="community",
                governance_proxy_id=proxy.id,
                config={},
            )
        )
        skill = Entity(
            entity_type=EntityType.skill,
            name="Pending Skill",
            owner_id=org_entity.id,
            creator_id=proxy.id,
            status=EntityStatus.pending,
            metadata_={},
        )
        self.db.add(skill)
        self.db.commit()

        pending = list_pending_for_actor(self.db, proxy.id)
        self.assertEqual(len(pending), 1)

        review_entity(self.db, skill, actor_entity_id=proxy.id, action="approve", feedback="Looks good")
        self.assertEqual(skill.status, EntityStatus.active)
        self.assertEqual(skill.metadata_["review"]["action"], "approve")


if __name__ == "__main__":
    unittest.main()
