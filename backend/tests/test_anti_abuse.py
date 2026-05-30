import unittest

from fastapi import HTTPException

from services.anti_abuse import require_evidence


class AntiAbuseTests(unittest.TestCase):
    def test_missing_evidence_rejected(self):
        with self.assertRaises(HTTPException) as ctx:
            require_evidence(None)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("Evidence is required", ctx.exception.detail)

    def test_empty_evidence_rejected(self):
        with self.assertRaises(HTTPException) as ctx:
            require_evidence({})
        self.assertEqual(ctx.exception.status_code, 400)

    def test_whitespace_only_evidence_rejected(self):
        with self.assertRaises(HTTPException) as ctx:
            require_evidence({"content_preview": "   "})
        self.assertEqual(ctx.exception.status_code, 400)

    def test_valid_evidence_passes(self):
        require_evidence({"content_preview": "real evidence text"})


if __name__ == "__main__":
    unittest.main()
