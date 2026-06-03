"""PL-6 — proof packet export carries dialogue_id refs from InvocationStep metadata."""

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models.contribution import ContributionEvent, ContributionStatus
from models.entity import Entity, EntityStatus, EntityType
from models.invocation import InvocationStatus, InvocationStep, InvocationTrace
from models.task import Task, TaskStatus
from services.pow_export import proof_packet_to_pow_record
from services.proof import build_contribution_proof_packet


class ProofDialogueRefsTests(unittest.TestCase):
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
        self.skill = Entity(
            entity_type=EntityType.skill,
            name="Tutor",
            status=EntityStatus.active,
        )
        self.db.add_all([self.human, self.skill])
        self.db.flush()

        task = Task(title="Study", sponsor_id=self.human.id, status=TaskStatus.open)
        self.db.add(task)
        self.db.flush()

        self.contrib = ContributionEvent(
            task_id=task.id,
            primary_entity_id=self.human.id,
            contribution_type="study_notes",
            description="Notes",
            status=ContributionStatus.submitted,
            evidence={"items": []},
        )
        self.db.add(self.contrib)
        self.db.flush()

        trace = InvocationTrace(
            initiator_id=self.human.id,
            contribution_id=self.contrib.id,
            status=InvocationStatus.completed,
        )
        self.db.add(trace)
        self.db.flush()
        self.db.add(
            InvocationStep(
                trace_id=trace.id,
                step_order=1,
                source_entity_id=self.human.id,
                target_entity_id=self.skill.id,
                action="uses",
                metadata_={
                    "dialogue_id": "dlg_pl6_1",
                    "dialogue_kind": "invoke",
                },
            )
        )
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_proof_includes_dialogue_refs_from_step_metadata(self):
        packet = build_contribution_proof_packet(self.db, self.contrib.id)
        self.assertIsNotNone(packet)
        assert packet is not None

        traces = packet["invocation_trace"]["traces"]
        self.assertEqual(len(traces), 1)
        dialogue_refs = traces[0]["dialogue_refs"]
        self.assertEqual(len(dialogue_refs), 1)
        self.assertEqual(dialogue_refs[0]["step_order"], 1)
        self.assertEqual(dialogue_refs[0]["dialogue_id"], "dlg_pl6_1")
        self.assertEqual(dialogue_refs[0]["dialogue_kind"], "invoke")

        step_meta = traces[0]["steps"][0]["metadata"]
        self.assertEqual(step_meta["dialogue_id"], "dlg_pl6_1")

    def test_pow_export_preserves_dialogue_refs(self):
        packet = build_contribution_proof_packet(self.db, self.contrib.id)
        self.assertIsNotNone(packet)
        assert packet is not None

        record = proof_packet_to_pow_record(packet)
        traces = record["invocation_traces"]["traces"]
        self.assertEqual(traces[0]["dialogue_refs"][0]["dialogue_id"], "dlg_pl6_1")


if __name__ == "__main__":
    unittest.main()
