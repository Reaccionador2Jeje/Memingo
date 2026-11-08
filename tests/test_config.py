import re
import unittest
from pathlib import Path

import memingo
from memingo.config import DEFAULT_LOCKFILE, DEFAULT_MANIFEST, DEFAULT_REGISTRY


ROOT = Path(__file__).resolve().parent.parent
version = memingo.__version__


class ConfigTests(unittest.TestCase):
    def test_versions_are_in_sync(self):
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        match = re.search(r'^version = "([^"]+)"', pyproject, re.MULTILINE)
        self.assertIsNotNone(match)
        self.assertEqual(memingo.__version__, version)
        self.assertEqual(match.group(1), version)

    def test_shared_defaults(self):
        self.assertTrue(DEFAULT_REGISTRY.endswith("/mgoa/index.json"))
        self.assertEqual(DEFAULT_MANIFEST, "memingo.toml")
        self.assertEqual(DEFAULT_LOCKFILE, "memingo.lock.json")


if __name__ == "__main__":
    unittest.main()
