"""Locale resolution and ontology localization."""

import unittest

from services.i18n import (
    locale_from_request,
    ontology_document_for_locale,
    pick_localized,
)


class TestI18n(unittest.TestCase):
    def test_locale_from_accept_language(self):
        self.assertEqual(locale_from_request("zh-CN,zh;q=0.9"), "zh")
        self.assertEqual(locale_from_request("en-US,en;q=0.9"), "en")

    def test_locale_query_overrides_header(self):
        self.assertEqual(locale_from_request("en-US", "zh"), "zh")

    def test_pick_localized(self):
        row = {"name": "Human", "name_zh": "人类"}
        self.assertEqual(pick_localized(row, "name", "en"), "Human")
        self.assertEqual(pick_localized(row, "name", "zh"), "人类")

    def test_ontology_document_zh(self):
        from intelligence.entity_ontology import ontology_document

        doc = ontology_document_for_locale(ontology_document(), "zh")
        self.assertEqual(doc["locale"], "zh")
        self.assertIn("贡献", doc["principle"])
        self.assertEqual(doc["entity_types"]["human"]["label"], "人类")


if __name__ == "__main__":
    unittest.main()
