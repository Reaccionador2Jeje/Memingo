import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from memingo.__main__ import main
from memingo.packages import resolve_entry


class CliErrorHandlingTests(unittest.TestCase):
    def run_cli(self, arguments):
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream), contextlib.redirect_stderr(stream):
            code = main(arguments)
        return code, stream.getvalue()

    def test_invalid_utf8_file_is_clean_error(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "binary.mgo"
            source.write_bytes(b"\xff\xfe\x00\x00")
            code, output = self.run_cli(["run", str(source)])
            self.assertEqual(code, 1)
            self.assertNotIn("Traceback", output)
            self.assertIn("UTF-8", output)

    def test_invalid_entry_type_is_clean_error(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "memingo.toml").write_text(
                '[package]\nname = "bad"\nversion = "0.1.0"\nentry = 123\n',
                encoding="utf-8",
            )
            code, output = self.run_cli(["run", temporary])
            self.assertEqual(code, 1)
            self.assertNotIn("Traceback", output)
            self.assertIn("entry", output)

    def test_entry_cannot_escape_project(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "memingo.toml").write_text(
                '[package]\nname = "escape"\nversion = "0.1.0"\nentry = "../outside.mgo"\n',
                encoding="utf-8",
            )
            code, output = self.run_cli(["run", temporary])
            self.assertEqual(code, 1)
            self.assertNotIn("Traceback", output)
            self.assertIn("inside the project", output)

    def test_missing_package_section_is_clean_error(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "memingo.toml").write_text('[dependencies]\n', encoding="utf-8")
            code, output = self.run_cli(["run", temporary])
            self.assertEqual(code, 1)
            self.assertNotIn("Traceback", output)
            self.assertIn("[package]", output)

    def test_fmt_invalid_encoding_is_clean_error(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "binary.mgo"
            source.write_bytes(b"\xff\xfe\x00\x00")
            code, output = self.run_cli(["fmt", str(source)])
            self.assertEqual(code, 1)
            self.assertNotIn("Traceback", output)
            self.assertIn("fmt", output)

    def test_build_invalid_entry_is_clean_error(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "memingo.toml").write_text(
                '[package]\nname = "bad"\nversion = "0.1.0"\nentry = []\n',
                encoding="utf-8",
            )
            code, output = self.run_cli(["build", temporary])
            self.assertEqual(code, 1)
            self.assertNotIn("Traceback", output)

    def test_resolve_entry_accepts_nested_entries(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "src").mkdir()
            (root / "src" / "app.mgo").write_text('spill "ok"\n', encoding="utf-8")
            (root / "memingo.toml").write_text(
                '[package]\nname = "nested"\nversion = "0.1.0"\nentry = "src/app.mgo"\n',
                encoding="utf-8",
            )
            _, entry, path = resolve_entry(root)
            self.assertEqual(entry, "src/app.mgo")
            self.assertEqual(path, (root / "src" / "app.mgo").resolve())

    def test_install_rejects_non_table_dependencies(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "memingo.toml").write_text(
                'dependencies = "nope"\n\n'
                '[package]\nname = "bad"\nversion = "0.1.0"\nentry = "main.mgo"\n',
                encoding="utf-8",
            )
            code, output = self.run_cli(["install", temporary])
            self.assertEqual(code, 1)
            self.assertNotIn("Traceback", output)
            self.assertIn("dependencies", output)

    def test_invalid_project_name_is_clean_error(self):
        with tempfile.TemporaryDirectory() as temporary:
            code, output = self.run_cli(["init", temporary, "--name", 'bad"name'])
            self.assertEqual(code, 1)
            self.assertNotIn("Traceback", output)
            self.assertIn("Project name", output)

    def test_corrupt_lockfile_is_clean_error(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "memingo.toml").write_text(
                '[package]\nname = "app"\nversion = "0.1.0"\nentry = "main.mgo"\n',
                encoding="utf-8",
            )
            (root / "main.mgo").write_text('borrow "missing"\n', encoding="utf-8")
            (root / "memingo.lock.json").write_text("{not json", encoding="utf-8")
            code, output = self.run_cli(["run", temporary])
            self.assertEqual(code, 1)
            self.assertNotIn("Traceback", output)
            self.assertIn("lockfile", output)


if __name__ == "__main__":
    unittest.main()
