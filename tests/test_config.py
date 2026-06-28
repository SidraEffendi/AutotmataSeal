import os
import unittest
from unittest.mock import patch

from config import has_groq_api_key, normalize_groq_api_key


class ConfigTests(unittest.TestCase):
    def test_grok_api_key_alias_populates_groq_api_key(self):
        with patch.dict(os.environ, {"GROK_API_KEY": "alias-key"}, clear=True):
            normalize_groq_api_key()
            self.assertEqual(os.environ["GROQ_API_KEY"], "alias-key")
            self.assertTrue(has_groq_api_key())

    def test_existing_groq_api_key_takes_precedence(self):
        with patch.dict(os.environ, {"GROQ_API_KEY": "primary-key", "GROK_API_KEY": "alias-key"}, clear=True):
            normalize_groq_api_key()
            self.assertEqual(os.environ["GROQ_API_KEY"], "primary-key")

    def test_missing_groq_keys_returns_false(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(has_groq_api_key())


if __name__ == "__main__":
    unittest.main()
