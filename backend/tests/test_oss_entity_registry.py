import unittest
from unittest.mock import MagicMock

from services.oss_entity_registry import (
    ensure_all_oss_entities,
    list_oss_entity_specs,
    _default_neural_entity_id,
)


class OssEntityRegistryTests(unittest.TestCase):
    def test_default_neural_entity_id(self):
        self.assertEqual(_default_neural_entity_id("sentence_transformers"), "pocp-oss-nn-sentence-transformers")

    def test_list_oss_entity_specs_includes_neural_and_community(self):
        specs = list_oss_entity_specs()
        slugs = {s["slug"] for s in specs}
        self.assertIn("ollama", slugs)
        self.assertIn("fastapi", slugs)
        self.assertIn("huggingface", slugs)

    def test_ensure_all_oss_entities_creates_rows(self):
        db = MagicMock()
        db.get.return_value = None
        org = MagicMock()
        org.id = "org-1"
        db.query.return_value.filter.return_value.first.return_value = org

        summary = ensure_all_oss_entities(db)
        self.assertGreater(summary["total"], 10)
        self.assertTrue(db.add.called)
        db.flush.assert_called()


if __name__ == "__main__":
    unittest.main()
