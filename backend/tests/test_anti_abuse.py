import unittest
from unittest.mock import MagicMock, patch

from fastapi import HTTPException

from models.contribution import ContributionEvent, ContributionStatus
from services.anti_abuse import (
    check_daily_ai_burn_limit,
    check_daily_contribution_limit,
    require_evidence,
)
from services.contribution import approve_contribution


class AntiAbuseTests(unittest.TestCase):
    def test_missing_evidence_rejected(self):
        with self.assertRaises(HTTPException) as ctx:
            require_evidence(None)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("Evidence is required", ctx.exception.detail)

    def test_empty_evidence_rejected(self):
        with self.assertRaises(HTTPException) as ctx:
            require_evidence({})
        self.assertEqual(ctx.exception.status_code, 400)

    def test_whitespace_only_evidence_rejected(self):
        with self.assertRaises(HTTPException) as ctx:
            require_evidence({"content_preview": "   "})
        self.assertEqual(ctx.exception.status_code, 400)

    def test_valid_evidence_passes(self):
        require_evidence({"content_preview": "real evidence text"})

    @patch("services.anti_abuse.DAILY_CONTRIBUTION_LIMIT", 10)
    def test_daily_contribution_limit_at_cap(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.scalar.return_value = 10
        with self.assertRaises(HTTPException) as ctx:
            check_daily_contribution_limit(db, "entity-1")
        self.assertEqual(ctx.exception.status_code, 429)
        self.assertIn("Daily contribution limit", ctx.exception.detail)

    @patch("services.anti_abuse.DAILY_CONTRIBUTION_LIMIT", 10)
    def test_daily_contribution_under_limit(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.scalar.return_value = 9
        check_daily_contribution_limit(db, "entity-1")

    @patch("services.anti_abuse.DAILY_AI_CREDITS_BURN_LIMIT", 200.0)
    def test_daily_ai_burn_limit_exceeded(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.scalar.return_value = 195.0
        with self.assertRaises(HTTPException) as ctx:
            check_daily_ai_burn_limit(db, "entity-1", 10.0)
        self.assertEqual(ctx.exception.status_code, 429)

    @patch("services.anti_abuse.DAILY_AI_CREDITS_BURN_LIMIT", 200.0)
    def test_daily_ai_burn_under_limit(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.scalar.return_value = 100.0
        check_daily_ai_burn_limit(db, "entity-1", 5.0)


class EntityEqualFinalizationTests(unittest.TestCase):
    def test_creator_may_finalize_under_entity_equal_policy(self):
        from services.contribution import approve_contribution

        contribution = ContributionEvent(
            primary_entity_id="rain-id",
            status=ContributionStatus.ai_verified,
            participants=[],
        )
        with patch("services.contribution.issue_contribution_rights", return_value=[]):
            with patch("services.contribution.append_ledger_record"):
                with patch("services.contribution.dispatch_review_event"):
                    rewards = approve_contribution(MagicMock(), contribution, reviewer_id="rain-id")
        self.assertEqual(rewards, {"credits": [], "reputation": []})


if __name__ == "__main__":
    unittest.main()
