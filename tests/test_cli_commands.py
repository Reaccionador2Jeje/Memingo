import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from memingo.__main__ import main
from memingo.packages import add_dependency


class CliCommandTests(unittest.TestCase):
    def run_cli(self, arguments):
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream), contextlib.redirect_stderr(stream):
            code = main(arguments)
        return code, stream.getvalue()

    def test_eval_runs_inline_code(self):
        code, output = self.run_cli(["eval", "spill 2 + 2"])
        self.assertEqual(code, 0)
        self.assertIn("4", output)

    def test_eval_reports_friendly_errors(self):
        code, output = self.run_cli(["eval", "vibe = 4"])
        self.assertEqual(code, 1)
        self.assertNotIn("Traceback", output)
        self.assertIn("Memingo error", output)

    def test_check_accepts_valid_files_and_rejects_invalid_ones(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            valid = root / "valid.mgo"
            valid.write_text('spill "ok"\n', encoding="utf-8")
            code, output = self.run_cli(["check", str(valid)])
            self.assertEqual(code, 0)
            self.assertIn("checked", output)

            invalid = root / "invalid.mgo"
            invalid.write_text("vibe = 4\n", encoding="utf-8")
            code, output = self.run_cli(["check", str(invalid)])
            self.assertEqual(code, 1)
            self.assertNotIn("Traceback", output)
            self.assertIn("Memingo error", output)

    def test_info_and_deps_show_project_data(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.assertEqual(self.run_cli(["init", temporary, "--name", "info-app"])[0], 0)
            add_dependency(root, "meme-core=1.2.0")

            code, output = self.run_cli(["info", temporary])
            self.assertEqual(code, 0)
            self.assertIn("info-app", output)
            self.assertIn("meme-core", output)

            code, output = self.run_cli(["deps", temporary])
            self.assertEqual(code, 0)
            self.assertIn("meme-core", output)
            self.assertIn("1.2.0", output)

    def test_clean_removes_generated_paths_and_supports_dry_run(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.assertEqual(self.run_cli(["init", temporary, "--name", "clean-app"])[0], 0)
            (root / ".memingo").mkdir()
            (root / "dist").mkdir()
            (root / "__pycache__").mkdir()

            code, output = self.run_cli(["clean", temporary, "--dry-run"])
            self.assertEqual(code, 0)
            self.assertIn("Would remove", output)
            self.assertTrue((root / ".memingo").exists())

            code, output = self.run_cli(["clean", temporary])
            self.assertEqual(code, 0)
            self.assertNotIn("Traceback", output)
            self.assertFalse((root / ".memingo").exists())
            self.assertFalse((root / "dist").exists())
            self.assertFalse((root / "__pycache__").exists())


if __name__ == "__main__":
    unittest.main()
