"""CI-11 governance PIP template + weighted vote scaffold tests (Sentinel-0)."""

import unittest

from services.anti_abuse import (
    compute_governance_power,
    pip_template_v0,
    reject_commercial_reputation_keys,
    tally_weighted_vote,
    validate_pip_proposal,
)


class GovernancePipTemplateTests(unittest.TestCase):
    def test_pip_template_has_required_fields(self):
        template = pip_template_v0()
        self.assertEqual(template["schema_version"], "pip-v0")
        self.assertIn("vote", template)
        self.assertIn("weight_factors", template["vote"])

    def test_validate_pip_proposal_requires_schema(self):
        with self.assertRaises(ValueError):
            validate_pip_proposal({"proposal_type": "x", "title": "t", "summary": "s", "vote": {}})

    def test_commercial_keys_in_vote_block_rejected(self):
        proposal = pip_template_v0()
        proposal["title"] = "Test"
        proposal["summary"] = "Summary"
        proposal["vote"]["commercial_ranking"] = True
        with self.assertRaises(ValueError):
            validate_pip_proposal(proposal)

    def test_commercial_keys_at_proposal_root_rejected(self):
        proposal = pip_template_v0()
        proposal["title"] = "Test"
        proposal["summary"] = "Summary"
        proposal["neural_rank_score"] = 0.99
        with self.assertRaises(ValueError):
            validate_pip_proposal(proposal)


class WeightedVoteScaffoldTests(unittest.TestCase):
    def test_governance_power_product(self):
        power = compute_governance_power(
            {
                "stake": 2.0,
                "reputation_coefficient": 1.5,
                "recent_contribution_coefficient": 1.0,
                "role_eligibility": 1.0,
                "risk_adjustment": 0.5,
            },
        )
        self.assertAlmostEqual(power, 1.5)

    def test_tally_weighted_vote_approve_majority(self):
        result = tally_weighted_vote(
            [
                {"entity_id": "voter-a", "ballot": "approve"},
                {"entity_id": "voter-b", "ballot": "reject"},
            ],
            {
                "voter-a": {
                    "stake": 2.0,
                    "reputation_coefficient": 1.0,
                    "recent_contribution_coefficient": 1.0,
                    "role_eligibility": 1.0,
                    "risk_adjustment": 1.0,
                },
                "voter-b": {
                    "stake": 1.0,
                    "reputation_coefficient": 1.0,
                    "recent_contribution_coefficient": 1.0,
                    "role_eligibility": 1.0,
                    "risk_adjustment": 1.0,
                },
            },
        )
        self.assertTrue(result["approved"])
        self.assertGreater(result["approve_weight"], result["reject_weight"])
        self.assertEqual(result["compat"], "pip-v0-scaffold")

    def test_reject_commercial_in_weight_factors(self):
        with self.assertRaises(ValueError):
            reject_commercial_reputation_keys({"optimizer_model": "proprietary-v2"})


if __name__ == "__main__":
    unittest.main()
