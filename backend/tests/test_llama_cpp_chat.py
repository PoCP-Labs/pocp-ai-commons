"""Tests for llama.cpp AI chat provider."""

import asyncio
import json
import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from services.ai_chat import generate_ai_reply
from services.llama_cpp_client import llama_cpp_chat_enabled


class _FakeChatResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {"choices": [{"message": {"content": "Hello from llama.cpp"}}]}


class LlamaCppChatTests(unittest.TestCase):
    @patch.dict(os.environ, {"ENABLE_LLAMA_CPP_CHAT": "true"}, clear=False)
    def test_llama_cpp_chat_enabled(self):
        self.assertTrue(llama_cpp_chat_enabled())

    @patch.dict(os.environ, {"ENABLE_LLAMA_CPP_CHAT": "true"}, clear=False)
    def test_generate_ai_reply_llama_cpp(self):
        async def _run():
            mock_client = MagicMock()
            mock_client.post = AsyncMock(return_value=_FakeChatResponse())
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            with patch("services.ai_chat.httpx.AsyncClient", return_value=mock_client):
                return await generate_ai_reply("hi", provider="llama_cpp")

        content, provider, model = asyncio.run(_run())
        self.assertEqual(provider, "llama_cpp")
        self.assertEqual(content, "Hello from llama.cpp")


if __name__ == "__main__":
    unittest.main()
