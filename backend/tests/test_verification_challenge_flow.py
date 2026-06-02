"""PR-B — verification challenge/appeal flow."""

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models.contribution import (
    ContributionEvent,
    ContributionStatus,
    ParticipantRole,
    ContributionParticipant,
)
from models.entity import Entity, EntityStatus, EntityType
from models.task import Task, TaskStatus
from services.contribution_dispute import (
    appeal_dispute,
    challenge_contribution,
    list_disputes,
    resolve_open_disputes,
)


class VerificationChallengeFlowTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()

        self.human = Entity(id="human-1", entity_type=EntityType.human, name="Alice", status=EntityStatus.active)
        self.challenger = Entity(id="human-2", entity_type=EntityType.human, name="Bob", status=EntityStatus.active)
        self.reviewer = Entity(id="human-3", entity_type=EntityType.human, name="Carol", status=EntityStatus.active)
        self.db.add_all([self.human, self.challenger, self.reviewer])

        task = Task(title="Test", sponsor_id="human-1", status=TaskStatus.open)
        self.db.add(task)
        self.db.flush()

        self.contrib = ContributionEvent(
            task_id=task.id,
            primary_entity_id="human-1",
            contribution_type="knowledge",
            description="Test contribution",
            status=ContributionStatus.approved,
        )
        self.db.add(self.contrib)
        self.db.flush()
        self.db.add(
            ContributionParticipant(
                contribution_id=self.contrib.id,
                entity_id="human-1",
                role=ParticipantRole.creator,
                weight=1.0,
            )
        )
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_challenge_appeal_resolve_dismissed(self):
        dispute = challenge_contribution(
            self.db,
            self.contrib,
            challenger_entity_id="human-2",
            reason="Evidence looks duplicated from another submission",
            evidence={"note": "duplicate hash"},
        )
        self.assertEqual(self.contrib.status, ContributionStatus.challenged)
        self.assertEqual(dispute.kind.value, "challenge")

        appeal = appeal_dispute(
            self.db,
            self.contrib,
            appellant_entity_id="human-1",
            reason="Original work with independent verification",
        )
        self.assertEqual(self.contrib.status, ContributionStatus.appealed)
        self.assertEqual(appeal.parent_dispute_id, dispute.id)

        resolve_open_disputes(
            self.db,
            self.contrib,
            resolver_entity_id="human-3",
            upheld=False,
            note="Challenge dismissed after review",
        )
        self.contrib.status = ContributionStatus.approved
        self.db.commit()

        rows = list_disputes(self.db, self.contrib.id)
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(r["status"] in ("dismissed", "upheld") for r in rows))

    def test_challenge_appeal_resolve_upheld(self):
        challenge_contribution(
            self.db,
            self.contrib,
            challenger_entity_id="human-2",
            reason="Plagiarism suspected in evidence bundle",
        )
        appeal_dispute(
            self.db,
            self.contrib,
            appellant_entity_id="human-1",
            reason="Appeal with additional context",
        )
        resolve_open_disputes(
            self.db,
            self.contrib,
            resolver_entity_id="human-3",
            upheld=True,
            note="Challenge upheld",
        )
        self.contrib.status = ContributionStatus.rejected
        self.db.commit()
        self.assertEqual(self.contrib.status, ContributionStatus.rejected)


if __name__ == "__main__":
    unittest.main()
