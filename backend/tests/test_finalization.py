import os
import unittest
from unittest.mock import MagicMock, patch

from services.finalization import (
    build_proof_finalization_block,
    clear_finalization_policy_cache,
    evaluate_finalization_policy,
    evaluate_witness_quorum,
    is_auto_finalization_enabled,
    try_auto_finalize_after_verify,
)
from services.verdict import Verdict
from models.contribution import ContributionStatus


class FinalizationPolicyTests(unittest.TestCase):
    def tearDown(self):
        clear_finalization_policy_cache()
        for key in ("ENABLE_AUTO_FINALIZATION", "POCP_FINALIZER_ENTITY_ID"):
            os.environ.pop(key, None)

    def test_env_enables_auto_finalization(self):
        os.environ["ENABLE_AUTO_FINALIZATION"] = "true"
        clear_finalization_policy_cache()
        self.assertTrue(is_auto_finalization_enabled())

    def test_witness_quorum_eligible(self):
        consensus = {
            "passed": True,
            "avg_score": 0.82,
            "avg_risk": 0.2,
            "suggested_cp": 40,
            "disagreement_high": False,
            "provider_results": [{"provider": "mock", "quality": 0.8, "risk_score": 0.2}],
        }
        with patch("services.finalization.is_auto_finalization_enabled", return_value=True):
            result = evaluate_witness_quorum(consensus)
        self.assertTrue(result["eligible"])
        self.assertEqual(result["mode"], "witness_quorum")
        self.assertEqual(result["witness_count"], 1)
        self.assertIn("decision_id", result)
        self.assertEqual(result["verdict"], Verdict.PASS.value)

    def test_high_cp_verdict_escalate(self):
        consensus = {
            "passed": True,
            "avg_score": 0.9,
            "avg_risk": 0.1,
            "suggested_cp": 501,
            "disagreement_high": False,
            "provider_results": [{"provider": "mock", "quality": 0.9, "risk_score": 0.1}],
        }
        with patch("services.finalization.is_auto_finalization_enabled", return_value=True):
            result = evaluate_finalization_policy(consensus)
        self.assertFalse(result["eligible"])
        self.assertEqual(result["verdict"], Verdict.ESCALATE.value)
        self.assertTrue(result["checks"]["cp_over_cap"])

    def test_try_auto_finalize_applies_when_eligible(self):
        contribution = MagicMock()
        contribution.status = ContributionStatus.ai_verified
        contribution.primary_entity_id = "human-1"
        contribution.id = "contrib-1"

        consensus = {
            "passed": True,
            "avg_score": 0.85,
            "avg_risk": 0.15,
            "suggested_cp": 30,
            "disagreement_high": False,
            "provider_results": [{"provider": "mock", "quality": 0.85, "risk_score": 0.15}],
        }

        db = MagicMock()
        with patch("services.finalization.is_auto_finalization_enabled", return_value=True):
            with patch(
                "services.finalization.approve_contribution",
                return_value={"credits": [{"entity_id": "human-1"}]},
            ) as approve:
                outcome = try_auto_finalize_after_verify(db, contribution, consensus)

        self.assertIsNotNone(outcome)
        assert outcome is not None
        self.assertTrue(outcome["applied"])
        approve.assert_called_once()
        args, kwargs = approve.call_args
        self.assertEqual(kwargs["finalization"]["mode"], "witness_quorum")
        self.assertTrue(kwargs["finalization"]["applied"])
        self.assertIn("decision_id", kwargs["finalization"])
        self.assertEqual(kwargs["finalization"]["verdict"], Verdict.PASS.value)

    def test_escalate_auto_finalize_when_enabled(self):
        contribution = MagicMock()
        contribution.status = ContributionStatus.ai_verified
        contribution.primary_entity_id = "human-1"
        contribution.id = "contrib-1"

        consensus = {
            "passed": True,
            "avg_score": 0.9,
            "avg_risk": 0.1,
            "suggested_cp": 501,
            "disagreement_high": False,
            "provider_results": [{"provider": "mock", "quality": 0.9, "risk_score": 0.1}],
        }

        db = MagicMock()
        with patch("services.finalization.is_auto_finalization_enabled", return_value=True):
            with patch("services.finalization.get_finalization_policy") as gp:
                gp.return_value = {"auto_finalize_on_escalate": True, "policy_id": "test"}
                with patch(
                    "services.finalization.approve_contribution",
                    return_value={"credits": []},
                ) as approve:
                    outcome = try_auto_finalize_after_verify(db, contribution, consensus)

        self.assertIsNotNone(outcome)
        assert outcome is not None
        self.assertTrue(outcome["applied"])
        self.assertTrue(outcome.get("escalated_auto_finalize"))
        approve.assert_called_once()

    def test_proof_finalization_block_from_ledger(self):
        contribution = MagicMock()
        contribution.status = ContributionStatus.approved
        contribution.human_reviews = [
            MagicMock(approved=True, reviewer_id="pocp-entity-clarion-0"),
        ]
        ledger = MagicMock()
        ledger.event_type = "contribution_approved"
        ledger.payload = {
            "finalization": {
                "mode": "witness_quorum",
                "policy_id": "genesis_witness_quorum_v1",
                "policy_version": "0.1",
                "finalizer_entity_id": "pocp-entity-clarion-0",
                "finalizer_role": "entity_delegate",
                "witness_summary": {"witness_count": 2},
            }
        }
        with patch("services.finalization.is_auto_finalization_enabled", return_value=True):
            block = build_proof_finalization_block(contribution, [ledger])
        self.assertEqual(block["mode"], "witness_quorum")
        self.assertEqual(block["finalizer_entity_id"], "pocp-entity-clarion-0")
        self.assertEqual(block["policy_id"], "genesis_witness_quorum_v1")


if __name__ == "__main__":
    unittest.main()
