"""Check dashboard source for embedded credentials and decorative emojis."""

import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class DashboardChecks(unittest.TestCase):
    def test_source_has_no_embedded_database_url(self):
        source = (ROOT / "test.py").read_text(encoding="utf-8")
        ast.parse(source)
        self.assertIn("URL.create(", source)
        self.assertNotIn("postgresql+psycopg2://", source)
        self.assertFalse(any(ord(ch) >= 0x1F300 for ch in source))

    def test_env_template_is_safe(self):
        source = (ROOT / ".env.example").read_text(encoding="utf-8")
        self.assertIn("DB_PASSWORD=replace_with_local_password", source)


if __name__ == "__main__":
    unittest.main()
