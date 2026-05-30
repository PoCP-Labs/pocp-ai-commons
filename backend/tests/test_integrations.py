import unittest

from services.agent_receipt import compute_receipt_hash, verify_agent_receipt
from services.provenance import attach_provenance_to_evidence, build_provenance_envelope, provenance_from_evidence
from services.code_attribution_bridge import build_code_attribution_context
from services.verifier_registry import load_verifier_providers


class ProvenanceTests(unittest.TestCase):
    def test_attach_provenance_roundtrip(self):
        evidence = attach_provenance_to_evidence(
            {"url": "https://example.com"},
            declared_by_entity_id="entity-1",
            creation_mode="ai_assisted",
            ai_tools_used=["cursor"],
            human_experts_cited=["github:rain"],
        )
        envelope = provenance_from_evidence(evidence)
        self.assertEqual(envelope["creation_mode"], "ai_assisted")
        self.assertEqual(envelope["envelope_version"], "octp-compatible-v0.1")
        self.assertIn("integrity", envelope)

    def test_build_provenance_envelope(self):
        envelope = build_provenance_envelope(
            declared_by_entity_id="entity-1",
            creation_mode="human_written",
        )
        self.assertEqual(envelope["declared_by_entity_id"], "entity-1")


class AgentReceiptTests(unittest.TestCase):
    def test_receipt_hash_stable(self):
        payload = {
            "spec_version": "pocp.agent_receipt.v0.1",
            "trace_id": "t1",
            "steps": [],
        }
        self.assertEqual(compute_receipt_hash(payload), compute_receipt_hash(payload))

    def test_unsigned_receipt_verify_false(self):
        receipt = {
            "spec_version": "pocp.agent_receipt.v0.1",
            "trace_id": "t1",
            "steps": [],
            "integrity": {
                "receipt_hash": "abc",
                "signature": "def",
                "signer_public_key": "00",
            },
        }
        self.assertFalse(verify_agent_receipt(receipt))


class VerifierRegistryTests(unittest.TestCase):
    def test_load_builtin_mock_verifier(self):
        providers = load_verifier_providers()
        names = {p.provider_name for p in providers}
        self.assertIn("mock", names)

    def test_genesis_witnesses_loaded_by_default(self):
        providers = load_verifier_providers()
        names = {p.provider_name for p in providers}
        self.assertIn("lumen-0", names)
        self.assertIn("desui", names)
        self.assertIn("clarion-0", names)


class ClarionUnifiedTests(unittest.TestCase):
    def test_score_context_for_verifier(self):
        from services.clarion import score_context_for_verifier

        scored = score_context_for_verifier(
            {
                "task": {"title": "Docs", "description": "Write setup guide"},
                "contribution": {
                    "description": "Added setup guide for beginners",
                    "evidence": {"url": "https://example.com/guide"},
                },
                "participants": [{"entity_id": "e1", "role": "creator"}],
            }
        )
        self.assertGreater(scored["avg_score"], 0.0)
        self.assertIn("rationale", scored)


class EvidenceGitTests(unittest.TestCase):
    def test_extract_empty_evidence(self):
        from services.evidence_git import validate_git_commits

        report = validate_git_commits({})
        self.assertEqual(report["checked_count"], 0)


class AttributionMerkleTests(unittest.TestCase):
    def test_build_and_verify_merkle_proof(self):
        from services.attribution_merkle import build_attribution_merkle_proof, verify_attribution_merkle_proof

        proof = build_attribution_merkle_proof({"artifact": "backend/services/proof.py"})
        if proof["leaf_count"] == 0:
            self.skipTest("no builders matched in this environment")
        slug = proof["builders"][0]["slug"]
        self.assertTrue(verify_attribution_merkle_proof(proof, slug))


class ReviewQueueTests(unittest.TestCase):
    def test_review_queue_import(self):
        from services.review_queue import list_human_review_queue

        self.assertTrue(callable(list_human_review_queue))


class CodeAttributionBridgeTests(unittest.TestCase):
    def test_matches_backend_path_hint(self):
        context = build_code_attribution_context({"artifact": "backend/services/proof.py"})
        self.assertTrue(context["path_hints"])
        self.assertTrue(context["builders_involved"] or context["matched_paths"])


class PortableReputationTests(unittest.TestCase):
    def test_validate_evidence_full_shape(self):
        from services.evidence_validate import validate_evidence_full

        report = validate_evidence_full({"url": "https://example.com"})
        self.assertIn("urls", report)
        self.assertIn("git", report)


class ProvenanceClaimsTests(unittest.TestCase):
    def test_verification_claims_in_envelope(self):
        evidence = attach_provenance_to_evidence(
            {"url": "https://example.com"},
            declared_by_entity_id="entity-1",
            verification_claims=[{"claim_type": "self_reviewed", "details": "demo"}],
        )
        envelope = provenance_from_evidence(evidence)
        self.assertEqual(len(envelope.get("verification_claims") or []), 1)


if __name__ == "__main__":
    unittest.main()
