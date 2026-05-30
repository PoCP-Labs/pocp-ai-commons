import asyncio
import unittest
from unittest.mock import MagicMock, patch

from fastapi import HTTPException

from services.ai_chat import chat_and_burn_credits


class AICreditsBurnTests(unittest.TestCase):
    def test_insufficient_credits_blocks_chat(self):
        wallet = MagicMock()
        wallet.id = "wallet-1"
        wallet.ai_credits = 2.0

        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = wallet

        with patch("services.ai_chat.check_daily_ai_burn_limit"):
            with self.assertRaises(HTTPException) as ctx:
                asyncio.run(
                    chat_and_burn_credits(
                        db,
                        entity_id="entity-1",
                        message="hello",
                        provider="mock",
                    )
                )

        self.assertEqual(ctx.exception.status_code, 402)
        self.assertIn("Insufficient AI Credits", ctx.exception.detail)

    def test_chat_burns_credits_on_success(self):
        wallet = MagicMock()
        wallet.id = "wallet-1"
        wallet.ai_credits = 10.0

        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = wallet

        with patch("services.ai_chat.check_daily_ai_burn_limit"):
            with patch("services.ai_chat.append_ledger_record"):
                result = asyncio.run(
                    chat_and_burn_credits(
                        db,
                        entity_id="entity-1",
                        message="hello",
                        provider="mock",
                    )
                )

        self.assertEqual(result["credits_spent"], 5)
        self.assertEqual(result["remaining_credits"], 5.0)
        self.assertEqual(wallet.ai_credits, 5.0)
        self.assertIn("reply", result)


if __name__ == "__main__":
    unittest.main()
