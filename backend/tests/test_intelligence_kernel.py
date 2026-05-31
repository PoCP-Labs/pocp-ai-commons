import unittest

from intelligence.protocol import (
    CAPABILITY_LAYER_VERSION,
    UNIFIED_PRINCIPLE,
    UNIFIED_PRINCIPLE_ZH,
    entity_can_contribute,
    contribution_packet_header,
)
from intelligence.kernel import capability_layer


class CapabilityLayerTests(unittest.TestCase):
    def test_unified_principle(self):
        self.assertIn("contribution", UNIFIED_PRINCIPLE.lower())
        self.assertIn("贡献", UNIFIED_PRINCIPLE_ZH)

    def test_all_entity_types_can_contribute(self):
        header = contribution_packet_header()
        for entity_type in header["entity_types"]:
            self.assertTrue(entity_can_contribute(entity_type))

    def test_status_lists_modules(self):
        status = capability_layer.status()
        self.assertEqual(status["capability_layer_version"], CAPABILITY_LAYER_VERSION)
        self.assertEqual(status["modules_total"], 11)
        self.assertGreaterEqual(status["modules_active"], 7)

    def test_protocol_includes_modules(self):
        protocol = capability_layer.protocol()
        self.assertEqual(protocol["protocol_version"], "0.1")
        self.assertEqual(len(protocol["modules"]), 11)
        self.assertIn("stack", protocol)

    def test_protocol_stack_layers(self):
        stack = capability_layer.protocol_stack()
        self.assertEqual(len(stack["layers"]), 3)
        ids = {layer["id"] for layer in stack["layers"]}
        self.assertEqual(ids, {"protocol", "capability", "transaction"})
        capability = next(l for l in stack["layers"] if l["id"] == "capability")
        self.assertTrue(capability["build_here"])
        transaction = next(l for l in stack["layers"] if l["id"] == "transaction")
        self.assertFalse(transaction["build_here"])


if __name__ == "__main__":
    unittest.main()
