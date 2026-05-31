import unittest

from services.finalization import _distinct_witness_nodes, _evaluate_named_rules, get_finalization_policy


class WitnessDiversityTests(unittest.TestCase):
    def test_distinct_peer_nodes(self):
        consensus = {
            "avg_score": 0.8,
            "avg_risk": 0.2,
            "passed": True,
            "disagreement_high": False,
            "suggested_cp": 10,
            "provider_results": [
                {"provider": "mock", "quality": 0.8, "risk_score": 0.2},
                {"provider": "peer:node-a", "quality": 0.85, "risk_score": 0.1},
                {"provider": "peer:node-b", "quality": 0.82, "risk_score": 0.15},
            ],
        }
        self.assertEqual(_distinct_witness_nodes(consensus), 3)

    def test_witness_diversity_rule_default_passes_single_node(self):
        consensus = {
            "avg_score": 0.8,
            "avg_risk": 0.2,
            "passed": True,
            "disagreement_high": False,
            "suggested_cp": 10,
            "provider_results": [{"provider": "mock", "quality": 0.8, "risk_score": 0.2}],
        }
        checks = _evaluate_named_rules(consensus, get_finalization_policy())
        self.assertTrue(checks["witness_diversity"])

    def test_witness_diversity_requires_two_nodes_when_configured(self):
        policy = get_finalization_policy()
        rules = dict(policy.get("rules") or {})
        wq = dict(rules.get("witness_quorum") or {})
        wq["min_distinct_witness_nodes"] = 2
        rules["witness_quorum"] = wq
        policy = {**policy, "rules": rules}

        single = {
            "avg_score": 0.8,
            "avg_risk": 0.2,
            "passed": True,
            "disagreement_high": False,
            "suggested_cp": 10,
            "provider_results": [{"provider": "mock", "quality": 0.8, "risk_score": 0.2}],
        }
        checks_single = _evaluate_named_rules(single, policy)
        self.assertFalse(checks_single["witness_diversity"])

        multi = {
            **single,
            "provider_results": [
                {"provider": "mock", "quality": 0.8, "risk_score": 0.2},
                {"provider": "peer:node-b", "quality": 0.85, "risk_score": 0.1},
            ],
        }
        checks_multi = _evaluate_named_rules(multi, policy)
        self.assertTrue(checks_multi["witness_diversity"])


if __name__ == "__main__":
    unittest.main()
