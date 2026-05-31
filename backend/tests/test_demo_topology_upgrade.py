"""Tests for idempotent demo pilot topology upgrade."""

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from genesis import DESUI_ID, LUMEN_0_ID, RAIN_ID
from models.contribution import (
    ContributionEvent,
    ContributionParticipant,
    ContributionStatus,
    ParticipantRole,
)
from models.entity import Entity, EntityStatus, EntityType
from models.task import Task, TaskStatus
from seed import upgrade_demo_pilot_topology


class DemoTopologyUpgradeTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()

        rain = Entity(id=RAIN_ID, entity_type=EntityType.human, name="Rain", status=EntityStatus.active)
        bob = Entity(entity_type=EntityType.human, name="Bob", status=EntityStatus.active)
        lumen = Entity(id=LUMEN_0_ID, entity_type=EntityType.llm, name="Lumen-0", status=EntityStatus.active)
        desui = Entity(id=DESUI_ID, entity_type=EntityType.llm, name="DeSui", status=EntityStatus.active)
        agent = Entity(entity_type=EntityType.agent, name="StudyAgent", status=EntityStatus.active)
        skill = Entity(entity_type=EntityType.skill, name="R-Tutor Skill", status=EntityStatus.active)
        org = Entity(entity_type=EntityType.organization, name="PoCP AI Commons", status=EntityStatus.active)
        self.db.add_all([rain, bob, lumen, desui, agent, skill, org])
        self.db.flush()

        task = Task(
            title="Organize R Language Matrix Study Notes",
            sponsor_id=org.id,
            status=TaskStatus.completed,
        )
        self.db.add(task)
        self.db.flush()

        contrib = ContributionEvent(
            task_id=task.id,
            primary_entity_id=RAIN_ID,
            contribution_type="knowledge",
            description="Structured R matrix study notes with examples.",
            evidence={"skills_used": ["R-Tutor Skill"]},
            status=ContributionStatus.approved,
        )
        self.db.add(contrib)
        self.db.flush()
        self.contrib_id = contrib.id

        self.db.add_all(
            [
                ContributionParticipant(
                    contribution_id=contrib.id,
                    entity_id=RAIN_ID,
                    role=ParticipantRole.creator,
                    weight=0.4,
                ),
                ContributionParticipant(
                    contribution_id=contrib.id,
                    entity_id=agent.id,
                    role=ParticipantRole.executor,
                    weight=0.25,
                ),
                ContributionParticipant(
                    contribution_id=contrib.id,
                    entity_id=skill.id,
                    role=ParticipantRole.skill_provider,
                    weight=0.15,
                ),
                ContributionParticipant(
                    contribution_id=contrib.id,
                    entity_id=lumen.id,
                    role=ParticipantRole.verifier,
                    weight=0.025,
                ),
                ContributionParticipant(
                    contribution_id=contrib.id,
                    entity_id=desui.id,
                    role=ParticipantRole.verifier,
                    weight=0.025,
                ),
            ]
        )
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_upgrade_adds_tool_dataset_and_witness(self):
        changed = upgrade_demo_pilot_topology(self.db)
        self.assertTrue(changed)
        self.db.commit()

        participants = (
            self.db.query(ContributionParticipant)
            .filter(ContributionParticipant.contribution_id == self.contrib_id)
            .all()
        )
        roles = {p.role for p in participants}
        self.assertIn(ParticipantRole.witness, roles)
        self.assertIn(ParticipantRole.tool_provider, roles)
        self.assertIn(ParticipantRole.data_provider, roles)
        self.assertEqual(len(participants), 9)

        lumen_role = next(p.role for p in participants if p.entity_id == LUMEN_0_ID)
        self.assertEqual(lumen_role, ParticipantRole.witness)

        contrib = self.db.get(ContributionEvent, self.contrib_id)
        self.assertIn("R Docs MCP Tool", contrib.evidence.get("tools_used", []))

        changed_again = upgrade_demo_pilot_topology(self.db)
        self.assertFalse(changed_again)


if __name__ == "__main__":
    unittest.main()
