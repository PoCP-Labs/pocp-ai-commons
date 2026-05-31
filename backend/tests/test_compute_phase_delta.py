"""Phase δ — org mesh visibility, abuse limits, LAN/federation discovery."""

import unittest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from genesis import RAIN_ID
from models.entity import Entity, EntityStatus, EntityType
from services.anti_abuse import (
    check_compute_job_limits,
    require_contribution_bound_compute,
)
from services.compute_jobs import create_job_record
from services.compute_lan_discovery import discover_lan_compute_peers
from services.compute_mesh import (
    VISIBILITY_ORG_ONLY,
    VISIBILITY_PUBLIC,
    provider_visible_to_initiator,
    resolve_org_entity_id,
)
from services.compute_profile import list_compute_provider_entities, register_compute_profile
from tests.compute_test_db import make_compute_test_session


class ComputeMeshTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()

        self.org = Entity(
            id="org-1",
            entity_type=EntityType.organization,
            name="PoCP AI Commons",
            status=EntityStatus.active,
        )
        self.rain = Entity(
            id=RAIN_ID,
            entity_type=EntityType.human,
            name="Rain",
            status=EntityStatus.active,
            metadata_={"org_entity_id": "org-1"},
        )
        self.stranger = Entity(
            id="human-2",
            entity_type=EntityType.human,
            name="Stranger",
            status=EntityStatus.active,
        )
        self.private_gpu = Entity(
            id="gpu-private",
            entity_type=EntityType.llm,
            name="Private GPU",
            status=EntityStatus.active,
            owner_id=RAIN_ID,
        )
        self.db.add_all([self.org, self.rain, self.stranger, self.private_gpu])
        self.db.commit()

        register_compute_profile(
            self.db,
            self.private_gpu.id,
            {
                "offers": [{"capability": "llm_inference", "adapters": ["mock"]}],
                "endpoints": {"base_url": "http://127.0.0.1:8000"},
                "policy": {"accepts_public_jobs": False, "visibility": VISIBILITY_ORG_ONLY},
                "accountability": {"owner_entity_id": RAIN_ID},
            },
            owner_entity_id=RAIN_ID,
        )
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_resolve_org_entity_id(self):
        self.assertEqual(resolve_org_entity_id(self.db, RAIN_ID), "org-1")

    def test_org_only_visible_to_owner_not_stranger(self):
        profile = self.private_gpu.metadata_["compute_profile"]
        self.assertTrue(
            provider_visible_to_initiator(
                self.db,
                provider=self.private_gpu,
                profile=profile,
                initiator_entity_id=RAIN_ID,
            )
        )
        self.assertFalse(
            provider_visible_to_initiator(
                self.db,
                provider=self.private_gpu,
                profile=profile,
                initiator_entity_id="human-2",
            )
        )

    def test_mesh_filter_list_providers(self):
        all_providers = list_compute_provider_entities(
            self.db, capability="llm_inference", mesh_filter=False
        )
        self.assertEqual(len(all_providers), 1)

        rain_view = list_compute_provider_entities(
            self.db,
            capability="llm_inference",
            initiator_entity_id=RAIN_ID,
            mesh_filter=True,
        )
        self.assertEqual(len(rain_view), 1)

        stranger_view = list_compute_provider_entities(
            self.db,
            capability="llm_inference",
            initiator_entity_id="human-2",
            mesh_filter=True,
        )
        self.assertEqual(len(stranger_view), 0)


class ComputeAbuseTests(unittest.TestCase):
    def test_require_contribution_bound(self):
        with self.assertRaises(HTTPException):
            require_contribution_bound_compute(contribution_id=None, task_id=None)

    def test_daily_compute_job_limit(self):
        db = make_compute_test_session()
        try:
            for _ in range(50):
                create_job_record(
                    db,
                    capability="witness",
                    initiator_entity_id="human-1",
                    contribution_id="c1",
                    task_id=None,
                    constraints={},
                    selected_provider=None,
                    receipt=None,
                )
            db.commit()
            with patch("services.anti_abuse.DAILY_COMPUTE_JOB_LIMIT", 50):
                with self.assertRaises(HTTPException):
                    check_compute_job_limits(db, "human-1")
        finally:
            db.close()


class ComputeDiscoveryTests(unittest.TestCase):
    def test_lan_discovery_disabled_by_default(self):
        with patch("services.compute_lan_discovery.lan_discovery_enabled", return_value=False):
            result = discover_lan_compute_peers()
        self.assertFalse(result["enabled"])
        self.assertEqual(result["peer_count"], 0)


if __name__ == "__main__":
    unittest.main()
