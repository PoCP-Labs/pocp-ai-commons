import unittest

from services.agent_receipt import compute_receipt_hash, verify_agent_receipt
from services.provenance import attach_provenance_to_evidence, build_provenance_envelope, provenance_from_evidence
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
        self.assertTrue(any(p.provider_name == "mock" for p in providers))


if __name__ == "__main__":
    unittest.main()
