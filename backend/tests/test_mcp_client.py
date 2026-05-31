"""Tests for MCP JSON-RPC wire client."""

import asyncio
import json
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from services.mcp_client import McpClientError, _extract_tool_result, _parse_http_json_rpc, call_tool_stdio


class McpClientTests(unittest.TestCase):
    def test_extract_tool_result_success(self):
        result = _extract_tool_result(
            {
                "jsonrpc": "2.0",
                "id": 2,
                "result": {"content": [{"type": "text", "text": "ok"}], "isError": False},
            }
        )
        self.assertEqual(result["content"][0]["text"], "ok")

    def test_extract_tool_result_error(self):
        with self.assertRaises(McpClientError):
            _extract_tool_result({"jsonrpc": "2.0", "id": 2, "error": {"message": "boom"}})

    def test_parse_http_json_rpc_sse(self):
        response = MagicMock()
        response.headers = {"content-type": "text/event-stream"}
        response.text = 'event: message\ndata: {"jsonrpc":"2.0","id":2,"result":{"content":[],"isError":false}}\n\n'
        parsed = _parse_http_json_rpc(response)
        self.assertEqual(parsed["id"], 2)

    def test_call_tool_stdio_happy_path(self):
        init_resp = json.dumps(
            {"jsonrpc": "2.0", "id": 1, "result": {"protocolVersion": "2024-11-05", "capabilities": {}}}
        ).encode()
        call_resp = json.dumps(
            {
                "jsonrpc": "2.0",
                "id": 2,
                "result": {"content": [{"type": "text", "text": "2026-05-29"}], "isError": False},
            }
        ).encode()

        async def _run() -> dict:
            stdout = asyncio.StreamReader()
            stdout.feed_data(init_resp + b"\n" + call_resp + b"\n")
            stdout.feed_eof()

            stdin = MagicMock()
            stdin.write = MagicMock()
            stdin.drain = AsyncMock()
            stdin.close = MagicMock()
            stdin.is_closing = MagicMock(return_value=False)

            proc = MagicMock()
            proc.stdin = stdin
            proc.stdout = stdout
            proc.stderr = asyncio.StreamReader()
            proc.wait = AsyncMock(return_value=0)

            with patch("services.mcp_client.asyncio.create_subprocess_exec", AsyncMock(return_value=proc)):
                return await call_tool_stdio(
                    {"transport": "stdio", "command": "echo", "args": []},
                    tool_name="get_current_time",
                    arguments={"timezone": "UTC"},
                    timeout=5,
                )

        result = asyncio.run(_run())
        self.assertIn("2026", result["content"][0]["text"])


if __name__ == "__main__":
    unittest.main()
