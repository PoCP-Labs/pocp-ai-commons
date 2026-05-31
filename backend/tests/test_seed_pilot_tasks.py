import unittest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models.entity import Entity, EntityStatus, EntityType
from models.task import Task
from scripts.seed_pilot_tasks import seed_pilot_tasks_db


class SeedPilotTasksTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        self.org = Entity(
            entity_type=EntityType.organization,
            name="PoCP AI Commons",
            status=EntityStatus.active,
        )
        self.db.add(self.org)
        self.db.commit()

    def tearDown(self):
        self.db.close()

    @patch("scripts.seed_pilot_tasks.SessionLocal")
    def test_seed_creates_tasks_idempotently(self, mock_session_local):
        mock_session_local.return_value = self.db
        first = seed_pilot_tasks_db(dry_run=False)
        count_after_first = self.db.query(Task).count()
        second = seed_pilot_tasks_db(dry_run=False)
        self.assertGreater(first["created"], 0)
        self.assertEqual(second["created"], 0)
        self.assertGreater(second["skipped"], 0)
        self.assertEqual(self.db.query(Task).count(), count_after_first)
        titles = [t.title for t in self.db.query(Task).all()]
        self.assertTrue(all(t.startswith("[Pilot]") for t in titles))


if __name__ == "__main__":
    unittest.main()
