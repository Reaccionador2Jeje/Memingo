import tempfile
import unittest
from pathlib import Path

from memingo.__main__ import main


class PackageCliTests(unittest.TestCase):
    def test_install_missing_project_manifest_auto_creates_project(self):
        with tempfile.TemporaryDirectory() as temporary:
            result = main(["install", temporary])
            self.assertEqual(result, 0)
            self.assertTrue((Path(temporary) / "memingo.toml").exists())
            self.assertTrue((Path(temporary) / "main.mgo").exists())

    def test_update_missing_project_manifest_auto_creates_project(self):
        with tempfile.TemporaryDirectory() as temporary:
            result = main(["update", temporary])
            self.assertEqual(result, 0)
            self.assertTrue((Path(temporary) / "memingo.toml").exists())

    def test_install_empty_project(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "memingo.toml").write_text(
                '[package]\nname = "empty"\nversion = "0.1.0"\nentry = "main.mgo"\n\n[dependencies]\n',
                encoding="utf-8",
            )
            self.assertEqual(main(["install", temporary]), 0)
            self.assertEqual(main(["update", temporary]), 0)


if __name__ == "__main__":
    unittest.main()
