"""Phase v0.2 — token metering, artifacts, intel receipts, capacity."""

import os
import unittest
from unittest.mock import patch

from services.compute_artifact import clear_artifact_store, lookup_artifact, store_artifact
from services.compute_capacity import clear_reservations, create_reservation, cancel_reservation
from services.compute_metering import (
    burn_credits_from_receipt,
    burn_tokens_from_receipt,
    consumer_credits_for_usage,
    estimate_token_usage,
    provider_credits_for_usage,
    settlement_block,
)
from services.compute_receipt import build_compute_receipt
from services.intel_receipt import build_intel_receipt, verify_intel_receipt
from services.protocol_config import get_rewards_config


class ComputeMeteringTests(unittest.TestCase):
    def setUp(self):
        get_rewards_config.cache_clear()

    def test_estimate_token_usage(self):
        usage = estimate_token_usage(prompt="hello", output="world")
        self.assertTrue(usage["estimated"])
        self.assertGreater(usage["total_tokens"], 0)

    def test_consumer_and_provider_credits(self):
        usage = {"metering_mode": "token", "prompt_tokens": 1000, "completion_tokens": 500, "total_tokens": 1500}
        consumer = consumer_credits_for_usage(usage, model="default")
        provider = provider_credits_for_usage(usage, model="default")
        self.assertGreaterEqual(consumer, 0.1)
        self.assertGreaterEqual(provider, 0.05)
        self.assertGreater(consumer, provider)

    def test_cache_hit_discount(self):
        usage = {"metering_mode": "token", "prompt_tokens": 2000, "completion_tokens": 1000, "total_tokens": 3000}
        live = consumer_credits_for_usage(usage, model="default", execution_mode="live_inference")
        cached = consumer_credits_for_usage(usage, model="default", execution_mode="cache_hit")
        self.assertLess(cached, live)

    def test_intel_witness_pricing(self):
        usage = {"metering_mode": "intel", "service": "witness", "intel_units": 1}
        self.assertEqual(provider_credits_for_usage(usage, model=None, capability="witness"), 3.0)
        self.assertEqual(consumer_credits_for_usage(usage, model=None, capability="witness"), 5.0)

    def test_settlement_block_unified(self):
        usage = estimate_token_usage(prompt="hi", output="there")
        block = settlement_block(usage, pocp_tokens_consumer=1.5, pocp_tokens_provider=0.5)
        self.assertTrue(block["unified_token"])
        self.assertEqual(block["token_unit"], "pocp_token")
        self.assertEqual(block["pocp_tokens_consumer"], 1.5)
        receipt = build_compute_receipt(
            provider_entity_id="llm-1",
            provider_node_id="n",
            capability="llm_inference",
            model="mock",
            input_material="prompt",
            output_material="output",
            extra={
                "usage": estimate_token_usage(prompt="prompt", output="output"),
                "execution_mode": "live_inference",
            },
        )
        self.assertGreater(burn_tokens_from_receipt(receipt), 0)


class IntelReceiptTests(unittest.TestCase):
    def test_build_and_verify(self):
        receipt = build_intel_receipt(
            provider_entity_id="skill-1",
            service="matching",
            contribution_id="c1",
        )
        self.assertTrue(verify_intel_receipt(receipt))
        self.assertEqual(receipt["service"], "matching")


class ComputeArtifactTests(unittest.TestCase):
    def setUp(self):
        clear_artifact_store()

    def test_store_and_lookup(self):
        store_artifact(model="m1", input_material="hello", output_material="world", provider_entity_id="p1")
        hit = lookup_artifact(model="m1", input_material="hello")
        self.assertIsNotNone(hit)
        self.assertEqual(hit["output_material"], "world")
        miss = lookup_artifact(model="m1", input_material="other")
        self.assertIsNone(miss)


class ComputeCapacityTests(unittest.TestCase):
    def setUp(self):
        clear_reservations()

    def test_create_and_cancel(self):
        record = create_reservation(
            consumer_entity_id="human-1",
            provider_entity_id="llm-1",
            capability="llm_inference",
            window_start="2026-06-01T02:00:00+00:00",
            window_end="2026-06-01T04:00:00+00:00",
            slots=1,
            prepaid_credits=10,
            contribution_id="c1",
        )
        self.assertEqual(record["status"], "active")
        cancelled = cancel_reservation(record["reservation_id"], consumer_entity_id="human-1")
        self.assertEqual(cancelled["status"], "cancelled")


if __name__ == "__main__":
    unittest.main()
