"""Tests for Trust Policy Bundle manifest and proof validation."""

import unittest

from fastapi import HTTPException

from services.trust_policy_bundle import (
    TRUST_POLICY_BUNDLE_SCHEMA,
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
            "primary": {
                "id": "h1",
                "entity_type": "human",
                "name": "Alice",
                "metadata": {"portable_id": "dev:alice"},
            },
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
            "trace_count": 1,
        },
    }
    proof.update(overrides)
    return proof


class TrustPolicyBundleTests(unittest.TestCase):
    def setUp(self):
        clear_trust_policy_bundle_cache()

    def tearDown(self):
        clear_trust_policy_bundle_cache()

    def test_manifest_has_core_components(self):
        manifest = trust_policy_bundle_manifest()
        self.assertEqual(manifest["schema"], TRUST_POLICY_BUNDLE_SCHEMA)
        self.assertIn("import_rules", manifest)
        self.assertIn("federation_trust", manifest)
        self.assertIn("finalization_policy", manifest)
        self.assertIn("entity_connections", manifest)
        self.assertIn("rights_rules", manifest)
        self.assertTrue(manifest.get("bundle_fingerprint"))

    def test_validate_minimal_proof_passes(self):
        result = validate_proof_against_trust_policy(
            _minimal_proof(),
            source_node_id="node-a",
            raise_on_block=False,
        )
        self.assertTrue(result["blocking_valid"])
        self.assertEqual(result["failed_count"], 0)

    def test_rejects_wrong_proof_type(self):
        with self.assertRaises(HTTPException) as ctx:
            validate_proof_against_trust_policy(
                _minimal_proof(proof_type="other"),
                raise_on_block=True,
            )
        self.assertEqual(ctx.exception.status_code, 400)

    def test_rejects_non_approved_status(self):
        proof = _minimal_proof()
        proof["contribution_event"] = {"id": "c1", "status": "submitted"}
        with self.assertRaises(HTTPException):
            validate_proof_against_trust_policy(proof, raise_on_block=True)

    def test_advisory_invocation_edge_mismatch_by_default(self):
        proof = _minimal_proof()
        proof["invocation_trace"]["traces"][0]["steps"][0]["action"] = "calls"
        result = validate_proof_against_trust_policy(proof, raise_on_block=False)
        self.assertTrue(result["blocking_valid"])
        self.assertGreater(result["failed_count"], 0)

    def test_rejects_bad_participant_role(self):
        proof = _minimal_proof()
        proof["entity_identity"]["participants"][0]["role"] = "skill_provider"
        result = validate_proof_against_trust_policy(proof, raise_on_block=False)
        self.assertGreater(result["failed_count"], 0)


if __name__ == "__main__":
    unittest.main()
