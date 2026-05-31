"""Tests for daily issuance budget caps."""

import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

from fastapi import HTTPException

from services.issuance_budget import assert_issuance_allowed, issuance_budget_status


class IssuanceBudgetTests(unittest.TestCase):
    def test_status_shape(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.group_by.return_value.all.return_value = []
        status = issuance_budget_status(db)
        self.assertTrue(status["enabled"])
        self.assertIn("remaining_today", status)
        self.assertIn("daily_cp", status["caps"])

    @patch("services.issuance_budget.daily_issued_totals", return_value={"cp": 4990, "ai_credits": 0})
    @patch("services.issuance_budget._budget_config")
    def test_daily_cp_cap_blocks(self, cfg, _totals):
        cfg.return_value = {
            "enabled": True,
            "daily_cp_cap": 5000,
            "daily_bc_cap": 20000,
            "per_contribution_cp_cap": 200,
            "per_contribution_bc_cap": 500,
        }
        with self.assertRaises(HTTPException) as ctx:
            assert_issuance_allowed(MagicMock(), cp_amount=20)
        self.assertEqual(ctx.exception.status_code, 429)

    @patch("services.issuance_budget.daily_issued_totals", return_value={"cp": 0, "ai_credits": 0})
    @patch("services.issuance_budget._budget_config")
    def test_per_contribution_cap_blocks(self, cfg, _totals):
        cfg.return_value = {
            "enabled": True,
            "daily_cp_cap": 5000,
            "daily_bc_cap": 20000,
            "per_contribution_cp_cap": 200,
            "per_contribution_bc_cap": 500,
        }
        with self.assertRaises(HTTPException):
            assert_issuance_allowed(MagicMock(), cp_amount=250)


class EntityEqualRightsTests(unittest.TestCase):
    def test_agent_bc_amount_when_enabled(self):
        from models.contribution import ParticipantRole
        from models.entity import EntityType
        from services.rights import entity_bc_amount

        participant = MagicMock(role=ParticipantRole.executor, weight=0.25)
        with patch("services.rights.entity_equal_enabled", return_value=True):
            with patch("services.rights.get_rewards_config") as cfg:
                cfg.return_value = {
                    "contribution_defaults": {"agent": {"ai_credits_base": 15}}
                }
                amount = entity_bc_amount(EntityType.agent, participant)
        self.assertEqual(amount, 15.0)


if __name__ == "__main__":
    unittest.main()
