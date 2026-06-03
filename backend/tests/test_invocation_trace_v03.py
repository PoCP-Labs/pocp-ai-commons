"""CI-6 — invocation trace state machine aligned with INVOCATION-SCHEMA-v0.3."""

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import models  # noqa: F401
from database import Base
from models.entity import Entity, EntityStatus, EntityType
from models.invocation import InvocationStatus
from models.skill import Skill
from services.invocation import (
    INVOCATION_TRACE_SPEC,
    add_invocation_step,
    complete_invocation_trace,
    fail_invocation_trace,
    record_invocation,
    start_invocation_trace,
    trace_to_v03_dict,
    transition_invocation_trace,
)


class InvocationTraceV03Tests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()

        self.human = Entity(entity_type=EntityType.human, name="Alice", status=EntityStatus.active)
        self.agent = Entity(entity_type=EntityType.agent, name="Agent", status=EntityStatus.active)
        self.skill_entity = Entity(
            entity_type=EntityType.skill, name="Tutor", status=EntityStatus.active
        )
        self.db.add_all([self.human, self.agent, self.skill_entity])
        self.db.flush()
        self.db.add(Skill(entity_id=self.skill_entity.id, version="1.0.0"))
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_trace_lifecycle_started_to_completed(self):
        trace = start_invocation_trace(self.db, initiator_id=self.human.id)
        self.assertEqual(trace.status, InvocationStatus.started)

        add_invocation_step(
            self.db,
            trace.id,
            source_entity_id=self.human.id,
            target_entity_id=self.agent.id,
            action="uses",
        )
        complete_invocation_trace(self.db, trace.id)
        self.db.refresh(trace)
        self.assertEqual(trace.status, InvocationStatus.completed)

        envelope = trace_to_v03_dict(trace)
        self.assertEqual(envelope["spec_version"], INVOCATION_TRACE_SPEC)
        self.assertEqual(envelope["initiator_entity_id"], self.human.id)
        self.assertEqual(envelope["status"], "completed")
        self.assertEqual(len(envelope["steps"]), 1)

    def test_invalid_transition_rejected(self):
        trace = start_invocation_trace(self.db, initiator_id=self.human.id)
        complete_invocation_trace(self.db, trace.id)
        with self.assertRaises(ValueError):
            transition_invocation_trace(self.db, trace.id, status="started")

    def test_fail_from_started(self):
        trace = start_invocation_trace(self.db, initiator_id=self.human.id)
        fail_invocation_trace(self.db, trace.id, reason="upstream timeout")
        self.db.refresh(trace)
        self.assertEqual(trace.status, InvocationStatus.failed)

    def test_record_invocation_uses_state_machine(self):
        trace = record_invocation(
            self.db,
            initiator_id=self.human.id,
            skill_entity_id=self.skill_entity.id,
            agent_entity_id=self.agent.id,
        )
        envelope = trace_to_v03_dict(trace)
        self.assertEqual(envelope["status"], "completed")
        self.assertEqual(len(envelope["steps"]), 2)
        self.assertEqual(envelope["steps"][0]["action"], "uses")
        self.assertEqual(envelope["steps"][1]["action"], "calls")


if __name__ == "__main__":
    unittest.main()
