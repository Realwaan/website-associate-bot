import tempfile
import unittest
from pathlib import Path

from ticket_loader import parse_ticket_markdown


class TestTicketLoader(unittest.TestCase):
    def test_parse_ticket_markdown_sections(self):
        content = """# Fix login redirect

**[PRIORITY]**

## Problem

Users are redirected to the wrong page.

## Potentially Related Files

- app/auth.py
- app/routes.py

## What to Fix

1. Normalize return URL parsing
2. Add fallback route

## Acceptance Criteria

- Redirect target is preserved after login
- Invalid return URL falls back safely
"""
        with tempfile.TemporaryDirectory() as tmp:
            file_path = Path(tmp) / "fix-login.md"
            file_path.write_text(content, encoding="utf-8")

            parsed = parse_ticket_markdown(str(file_path))

        self.assertEqual(parsed["name"], "fix-login")
        self.assertEqual(parsed["title"], "Fix login redirect")
        self.assertEqual(parsed["priority"], "PRIORITY")
        self.assertIn("wrong page", parsed["problem"])
        self.assertEqual(parsed["related_files"], ["app/auth.py", "app/routes.py"])
        self.assertEqual(
            parsed["what_to_fix"],
            ["Normalize return URL parsing", "Add fallback route"],
        )
        self.assertEqual(len(parsed["acceptance_criteria"]), 2)


if __name__ == "__main__":
    unittest.main()
