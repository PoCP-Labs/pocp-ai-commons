"""Tests for MCP invocation context in proof packets."""

import unittest
from unittest.mock import MagicMock

from services.mcp_invocation_context import (
    MCP_CONTEXT_SPEC,
    build_mcp_invocation_context,
    verify_mcp_context_receipt_hashes,
)


class McpInvocationContextTests(unittest.TestCase):
    def test_empty_invocations(self):
        ctx = build_mcp_invocation_context([], contribution_id="c1")
        self.assertEqual(ctx["spec_version"], MCP_CONTEXT_SPEC)
        self.assertEqual(ctx["trace_count"], 0)
        self.assertEqual(ctx["inspiration_slug"], "mcp")

    def test_mcp_steps_extracted(self):
        step = MagicMock()
        step.step_order = 1
        step.source_entity_id = "human-1"
        step.target_entity_id = "tool-1"
        step.action = "invokes_mcp"
        step.metadata_ = {
            "mcp_tool_name": "fetch",
            "mcp_server_id": "server-1",
            "mcp_spec_version": "2024-11-05",
            "invoke_mode": "live",
        }

        trace = MagicMock()
        trace.id = "trace-1"
        trace.initiator_id = "human-1"
        trace.model_provider = "mcp-live"
        trace.steps = [step]

        tool = MagicMock()
        tool.entity_type.value = "tool"
        tool.name = "Fetch MCP"

        ctx = build_mcp_invocation_context(
            [trace],
            contribution_id="c1",
            entities={"tool-1": tool},
        )
        self.assertEqual(ctx["trace_count"], 1)
        self.assertEqual(ctx["tool_step_count"], 1)
        self.assertIn("live", ctx["invoke_modes"])
        self.assertEqual(len(ctx["capability_receipt_hashes"]), 1)
        self.assertTrue(verify_mcp_context_receipt_hashes(ctx))


if __name__ == "__main__":
    unittest.main()
