"""Cursor-style LLM language policy (not UI i18n)."""

import unittest

from services.llm_language import (
    conversational_system_prompt,
    detect_language_hint,
    infer_context_language,
    mirror_user_language_enabled,
    verifier_system_prompt,
)


class TestLlmLanguage(unittest.TestCase):
    def test_detect_hint(self):
        self.assertEqual(detect_language_hint("帮我写贡献说明"), "zh")
        self.assertEqual(detect_language_hint("Help me draft a contribution"), "en")
        self.assertIn(
            detect_language_hint("Help 帮我 mixed"),
            ("mixed", "zh", "en"),
        )

    def test_system_prompt_mirror(self):
        prompt = conversational_system_prompt(base="Base.", domain="ai_chat")
        self.assertIn("Base.", prompt)
        self.assertIn("same language", prompt)

    def test_mirror_enabled_by_default(self):
        self.assertTrue(mirror_user_language_enabled())

    def test_verifier_system_prompt(self):
        prompt = verifier_system_prompt()
        self.assertIn("Return JSON only", prompt)
        self.assertIn("rationale", prompt)

    def test_infer_context_language(self):
        hint = infer_context_language(
            {"task": {"description": "矩阵笔记"}, "contribution": {"description": ""}}
        )
        self.assertEqual(hint, "zh")


if __name__ == "__main__":
    unittest.main()
