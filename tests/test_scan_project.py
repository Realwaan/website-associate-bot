import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from scan_project import (
    DETECTOR_DEBUG,
    DETECTOR_EMPTY_CATCH,
    DETECTOR_HARDCODED_SECRET,
    DETECTOR_TODO,
    _detect_in_file,
)


class TestScanProjectDetectors(unittest.TestCase):
    def test_enabled_detector_filtering(self):
        lines = [
            "# TODO: refactor this flow",
            "print('debugging')",
            "except Exception: pass",
            "api_key = 'secret-token-value'",
        ]

        todo_only = _detect_in_file(
            "app/main.py",
            lines,
            enabled_detectors={DETECTOR_TODO},
        )
        self.assertEqual(len(todo_only), 1)
        self.assertEqual(todo_only[0].category, DETECTOR_TODO)

        debug_and_secrets = _detect_in_file(
            "app/main.py",
            lines,
            enabled_detectors={DETECTOR_DEBUG, DETECTOR_HARDCODED_SECRET},
        )
        self.assertEqual({i.category for i in debug_and_secrets}, {DETECTOR_DEBUG, DETECTOR_HARDCODED_SECRET})
        self.assertNotIn(DETECTOR_EMPTY_CATCH, {i.category for i in debug_and_secrets})


if __name__ == "__main__":
    unittest.main()
