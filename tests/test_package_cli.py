import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from memingo.__main__ import main


def run_cli(arguments):
    stream = io.StringIO()
    with contextlib.redirect_stdout(stream), contextlib.redirect_stderr(stream):
        code = main(arguments)
    return code, stream.getvalue()


class PackageCliTests(unittest.TestCase):
    def test_install_creates_missing_manifest_and_directories(self):
        with tempfile.TemporaryDirectory() as temporary:
            code, output = run_cli(["install", temporary])
            self.assertEqual(code, 0)
            self.assertNotIn("Traceback", output)
            root = Path(temporary)
            self.assertTrue((root / "memingo.toml").is_file())
            self.assertTrue((root / ".memingo" / "packages").is_dir())
            manifest = (root / "memingo.toml").read_text(encoding="utf-8")
            self.assertIn("[package]", manifest)
            self.assertIn("[dependencies]", manifest)
            self.assertTrue((root / "main.mgo").is_file())

    def test_update_creates_missing_manifest(self):
        with tempfile.TemporaryDirectory() as temporary:
            code, output = run_cli(["update", temporary])
            self.assertEqual(code, 0)
            self.assertNotIn("Traceback", output)
            self.assertTrue((Path(temporary) / "memingo.toml").is_file())

    def test_install_does_not_overwrite_existing_manifest(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            original = '[package]\nname = "kept"\nversion = "9.9.9"\nentry = "main.mgo"\n\n[dependencies]\n'
            (root / "memingo.toml").write_text(original, encoding="utf-8")
            code, _ = run_cli(["install", temporary])
            self.assertEqual(code, 0)
            self.assertEqual((root / "memingo.toml").read_text(encoding="utf-8"), original)

    def test_install_empty_project(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "memingo.toml").write_text(
                '[package]\nname = "empty"\nversion = "0.1.0"\nentry = "main.mgo"\n\n[dependencies]\n',
                encoding="utf-8",
            )
            self.assertEqual(main(["install", temporary]), 0)
            self.assertEqual(main(["update", temporary]), 0)

    def test_manifest_command_creates_missing_manifest(self):
        with tempfile.TemporaryDirectory() as temporary:
            code, output = run_cli(["manifest", temporary, "--name", "manifest-app"])
            self.assertEqual(code, 0)
            self.assertTrue((Path(temporary) / "memingo.toml").is_file())
            self.assertIn("manifest-app", (Path(temporary) / "memingo.toml").read_text(encoding="utf-8"))
            self.assertIn("Manifest", output)

    def test_manifest_command_keeps_existing_manifest(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            original = '[package]\nname = "kept"\nversion = "1.0.0"\nentry = "main.mgo"\n'
            (root / "memingo.toml").write_text(original, encoding="utf-8")
            code, output = run_cli(["manifest", temporary])
            self.assertEqual(code, 0)
            self.assertEqual((root / "memingo.toml").read_text(encoding="utf-8"), original)
            self.assertIn("already exists", output)


if __name__ == "__main__":
    unittest.main()
