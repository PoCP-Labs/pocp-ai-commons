"""Tests for federation strict trust policy pilot."""

import os
import unittest

from services.trust_policy_bundle import (
    clear_trust_policy_bundle_cache,
    trust_policy_bundle_manifest,
    validate_proof_against_trust_policy,
)


def _minimal_proof(**overrides) -> dict:
    proof = {
        "proof_type": "pocp_contribution_proof",
        "contribution_event": {"id": "c1", "status": "approved"},
        "integrity": {"proof_hash": "abc123"},
        "evidence": {"content_hash": "ev-hash"},
        "entity_identity": {
            "primary": {"id": "h1", "entity_type": "human", "name": "Alice"},
            "participants": [
                {
                    "entity": {"id": "a1", "entity_type": "agent", "name": "Agent"},
                    "role": "executor",
                    "weight": 0.4,
                }
            ],
        },
        "invocation_trace": {
            "traces": [
                {
                    "id": "t1",
                    "steps": [
                        {
                            "step_order": 1,
                            "source_entity_id": "h1",
                            "target_entity_id": "a1",
                            "action": "uses",
                        }
                    ],
                }
            ],
        },
    }
    proof.update(overrides)
    return proof


class FederationStrictModeTests(unittest.TestCase):
    def tearDown(self):
        os.environ.pop("POCP_STRICT_TRUST_POLICY", None)
        clear_trust_policy_bundle_cache()

    def test_manifest_reports_strict_mode_env(self):
        manifest = trust_policy_bundle_manifest()
        self.assertEqual(manifest.get("strict_mode_env"), "POCP_STRICT_TRUST_POLICY")
        self.assertFalse(manifest.get("strict_mode_active"))

    def test_strict_mode_blocks_bad_role(self):
        proof = _minimal_proof()
        proof["entity_identity"]["participants"][0]["role"] = "skill_provider"
        os.environ["POCP_STRICT_TRUST_POLICY"] = "true"
        clear_trust_policy_bundle_cache()
        result = validate_proof_against_trust_policy(proof, raise_on_block=False)
        self.assertFalse(result["blocking_valid"])
        self.assertGreater(result["blocking_failed_count"], 0)

    def test_strict_mode_passes_valid_proof(self):
        os.environ["POCP_STRICT_TRUST_POLICY"] = "true"
        clear_trust_policy_bundle_cache()
        result = validate_proof_against_trust_policy(_minimal_proof(), raise_on_block=False)
        self.assertTrue(result["blocking_valid"])


if __name__ == "__main__":
    unittest.main()
