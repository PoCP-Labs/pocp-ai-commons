"""Provider-signed compute receipt (Phase 2b)."""

import os
import unittest
from unittest.mock import patch

from services.compute_receipt import (
    attach_provider_signature,
    build_compute_receipt,
    verify_compute_receipt,
    verify_provider_receipt_signature,
)


class ComputeReceiptSignatureTests(unittest.TestCase):
    def test_unsigned_receipt_still_valid(self):
        receipt = build_compute_receipt(
            provider_entity_id="prov-1",
            provider_node_id="node-a",
            capability="llm_inference",
            adapter="mock",
        )
        self.assertTrue(verify_compute_receipt(receipt))
        self.assertFalse(verify_provider_receipt_signature(receipt))

    @patch.dict(os.environ, {"POCP_SIGN_COMPUTE_RECEIPTS": "true"})
    @patch("services.federation_crypto.sign_message", return_value="sig-abc")
    @patch("services.federation_crypto.get_node_public_key_hex", return_value="pub-xyz")
    def test_attach_provider_signature(self, _pub, _sig):
        receipt = build_compute_receipt(
            provider_entity_id="prov-1",
            provider_node_id="node-a",
            capability="llm_inference",
            adapter="mock",
        )
        self.assertEqual(receipt["integrity"]["provider_signature"], "sig-abc")
        self.assertEqual(receipt["integrity"]["provider_public_key"], "pub-xyz")

    def test_verify_provider_signature_roundtrip(self):
        receipt = build_compute_receipt(
            provider_entity_id="prov-1",
            provider_node_id="node-a",
            capability="llm_inference",
            adapter="mock",
        )
        signed = dict(receipt)
        signed["integrity"] = dict(receipt["integrity"])
        signed["integrity"]["provider_signature"] = "sig-abc"
        signed["integrity"]["provider_public_key"] = "pub-xyz"
        with patch("services.federation_crypto.verify_message", return_value=True):
            self.assertTrue(verify_provider_receipt_signature(signed))


if __name__ == "__main__":
    unittest.main()
