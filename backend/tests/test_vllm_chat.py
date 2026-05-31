"""Tests for vLLM AI chat provider."""

import asyncio
import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from services.ai_chat import generate_ai_reply
from services.vllm_client import vllm_chat_enabled


class _FakeChatResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {"choices": [{"message": {"content": "Hello from vLLM"}}]}


class VllmChatTests(unittest.TestCase):
    @patch.dict(os.environ, {"ENABLE_VLLM_CHAT": "true"}, clear=False)
    def test_vllm_chat_enabled(self):
        self.assertTrue(vllm_chat_enabled())

    @patch.dict(os.environ, {"ENABLE_VLLM_CHAT": "true"}, clear=False)
    def test_generate_ai_reply_vllm(self):
        async def _run():
            mock_client = MagicMock()
            mock_client.post = AsyncMock(return_value=_FakeChatResponse())
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            with patch("services.ai_chat.httpx.AsyncClient", return_value=mock_client):
                return await generate_ai_reply("hi", provider="vllm")

        content, provider, model = asyncio.run(_run())
        self.assertEqual(provider, "vllm")
        self.assertEqual(content, "Hello from vLLM")


if __name__ == "__main__":
    unittest.main()
