"""v0.3 — surplus recycle, compute pool, utilization."""

import os
import unittest
from unittest.mock import patch
from datetime import datetime, timezone

from models.entity import Entity, EntityStatus, EntityType
from models.wallet import Wallet
from services.compute_artifact import clear_artifact_store, lookup_artifact
from services.compute_pool import deposit_to_pool, get_pool_summary, spend_from_pool
from services.compute_precompute import recycle_surplus, run_precompute_on_provider
from services.compute_balance_cron import (
    auto_balance_enabled,
    discover_balance_org_targets,
    run_auto_balance_cycle,
)
from services.compute_utilization import balance_summary, list_idle_providers, provider_utilization
from services.protocol_config import get_rewards_config


def _org(db, org_id: str = "org-1") -> Entity:
    e = Entity(
        id=org_id,
        entity_type=EntityType.organization,
        name="Rain Org",
        status=EntityStatus.active,
        metadata_={"compute_pool": {"balance_credits": 100.0, "total_deposited": 100.0, "total_spent": 0.0}},
    )
    db.add(e)
    return e


def _provider(db, pid: str = "llm-1", org_id: str = "org-1") -> Entity:
    e = Entity(
        id=pid,
        entity_type=EntityType.llm,
        name="Lab GPU",
        status=EntityStatus.active,
        metadata_={
            "compute_profile": {
                "spec_version": "0.1",
                "status": "active",
                "last_heartbeat": datetime.now(timezone.utc).isoformat(),
                "offers": [{"capability": "llm_inference", "adapters": ["ollama"]}],
                "endpoints": {"base_url": "http://127.0.0.1:11434"},
                "capacity": {"max_concurrent": 2},
                "policy": {"organization_entity_id": org_id, "visibility": "org_only"},
            }
        },
    )
    db.add(e)
    db.add(Wallet(entity_id=pid, ai_credits=10.0, cp_balance=0))
    return e


class ComputePoolTests(unittest.TestCase):
    def setUp(self):
        from tests.compute_test_db import make_compute_test_session

        self.db = make_compute_test_session()
        _org(self.db)
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_deposit_and_spend(self):
        summary = deposit_to_pool(self.db, "org-1", 50, reason="sponsor")
        self.assertEqual(summary["balance_credits"], 150.0)
        _provider(self.db)
        self.db.commit()
        spend_from_pool(self.db, "org-1", 5, reason="precompute", beneficiary_entity_id="llm-1")
        summary = get_pool_summary(self.db, "org-1")
        self.assertEqual(summary["balance_credits"], 145.0)


class ComputeUtilizationTests(unittest.TestCase):
    def setUp(self):
        from tests.compute_test_db import make_compute_test_session

        self.db = make_compute_test_session()
        _org(self.db)
        _provider(self.db)
        self.db.commit()
        get_rewards_config.cache_clear()

    def tearDown(self):
        self.db.close()

    def test_idle_provider_detected(self):
        stats = provider_utilization(self.db, "llm-1")
        self.assertTrue(stats["idle"])
        idle = list_idle_providers(self.db, organization_entity_id="org-1")
        self.assertEqual(len(idle), 1)

    def test_balance_summary_recommends_recycle(self):
        summary = balance_summary(self.db, organization_entity_id="org-1")
        self.assertEqual(summary["recommendation"], "surplus_detected_run_recycle")


class ComputeSurplusRecycleTests(unittest.TestCase):
    def setUp(self):
        from tests.compute_test_db import make_compute_test_session

        self.db = make_compute_test_session()
        clear_artifact_store()
        _org(self.db)
        _provider(self.db)
        self.db.commit()
        get_rewards_config.cache_clear()

    def tearDown(self):
        clear_artifact_store()
        self.db.close()

    def test_precompute_stores_artifact(self):
        result = run_precompute_on_provider(
            self.db,
            provider_entity_id="llm-1",
            organization_entity_id="org-1",
            task={
                "type": "artifact_warmup",
                "capability": "llm_inference",
                "model": "surplus-precompute",
                "prompts": ["test prompt for cache"],
            },
        )
        self.assertGreater(len(result["results"]), 0)
        hit = lookup_artifact(model="surplus-precompute", input_material="test prompt for cache")
        self.assertIsNotNone(hit)

    def test_recycle_surplus_cycle(self):
        out = recycle_surplus(self.db, organization_entity_id="org-1")
        self.assertEqual(out["status"], "completed")
        self.assertGreaterEqual(out["providers_recycled"], 1)


class ComputeAutoBalanceTests(unittest.TestCase):
    def setUp(self):
        from tests.compute_test_db import make_compute_test_session

        self.db = make_compute_test_session()
        clear_artifact_store()
        _org(self.db)
        _provider(self.db)
        self.db.commit()
        get_rewards_config.cache_clear()

    def tearDown(self):
        clear_artifact_store()
        self.db.close()

    def test_discover_org_targets(self):
        targets = discover_balance_org_targets(self.db)
        self.assertIn("org-1", targets)

    def test_auto_balance_dry_run_recycle(self):
        result = run_auto_balance_cycle(
            self.db, organization_entity_id="org-1", dry_run=True, force=True
        )
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["actions"][0]["action"], "would_recycle")

    def test_auto_balance_force_recycle(self):
        result = run_auto_balance_cycle(
            self.db, organization_entity_id="org-1", force=True
        )
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["actions"][0]["action"], "recycled")
        self.assertGreaterEqual(result["actions"][0]["recycle"]["providers_recycled"], 1)

    def test_auto_balance_skipped_when_disabled(self):
        result = run_auto_balance_cycle(self.db, organization_entity_id="org-1")
        self.assertEqual(result["status"], "skipped")

    def test_auto_balance_enabled_from_env(self):
        with patch.dict(os.environ, {"POCP_COMPUTE_AUTO_BALANCE": "true"}):
            get_rewards_config.cache_clear()
            self.assertTrue(auto_balance_enabled())


if __name__ == "__main__":
    unittest.main()
