"""Training contribution evidence validation tests."""

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import models  # noqa: F401
from database import Base
from fastapi import HTTPException
from genesis import RAIN_ID
from models.entity import Entity, EntityStatus, EntityType
from models.task import Task, TaskStatus
from services.contribution_submit import submit_contribution_event
from services.training_contribution import enrich_training_evidence, validate_training_evidence


def _valid_training_evidence():
    return {
        "_pocp": {"tags": ["training"]},
        "training": {
            "job_id": "train-001",
            "objective": "fine_tune_demo",
            "dataset_ref": "dataset:demo",
            "model_ref": "huggingface:org/model",
            "metrics": {"loss_final": 0.5},
        },
    }


class TrainingContributionTests(unittest.TestCase):
    def test_validate_requires_training_block(self):
        with self.assertRaises(ValueError):
            validate_training_evidence({"foo": "bar"})

    def test_validate_requires_fields(self):
        with self.assertRaises(ValueError):
            validate_training_evidence({"training": {"job_id": "x"}})

    def test_validate_ok(self):
        report = validate_training_evidence(_valid_training_evidence())
        self.assertTrue(report["valid"])
        self.assertEqual(report["schema_id"], "pocp.training_contribution.v0.1")

    def test_enrich_adds_standard(self):
        enriched = enrich_training_evidence(_valid_training_evidence())
        self.assertEqual(
            enriched["_pocp"]["evidence_standard"],
            "pocp.training_contribution.v0.1",
        )

    def test_submit_training_contribution(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        db = Session()

        rain = Entity(id=RAIN_ID, entity_type=EntityType.human, name="Rain", status=EntityStatus.active)
        task = Task(
            id="task-train-1",
            title="Train demo",
            description="Fine-tune",
            sponsor_id=RAIN_ID,
            status=TaskStatus.open,
        )
        db.add_all([rain, task])
        db.commit()

        contribution = submit_contribution_event(
            db,
            human_entity_id=RAIN_ID,
            task_id=task.id,
            contribution_type="training",
            description="Training run",
            evidence=_valid_training_evidence(),
        )
        self.assertEqual(contribution.contribution_type, "training")
        self.assertEqual(
            contribution.evidence["_pocp"]["evidence_standard"],
            "pocp.training_contribution.v0.1",
        )
        db.close()

    def test_submit_training_rejects_incomplete(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        db = Session()

        rain = Entity(id=RAIN_ID, entity_type=EntityType.human, name="Rain", status=EntityStatus.active)
        task = Task(
            id="task-train-2",
            title="Train demo",
            description="Fine-tune",
            sponsor_id=RAIN_ID,
            status=TaskStatus.open,
        )
        db.add_all([rain, task])
        db.commit()

        with self.assertRaises(HTTPException) as ctx:
            submit_contribution_event(
                db,
                human_entity_id=RAIN_ID,
                task_id=task.id,
                contribution_type="training",
                evidence={"training": {"job_id": "only-id"}},
            )
        self.assertEqual(ctx.exception.status_code, 400)
        db.close()


if __name__ == "__main__":
    unittest.main()
