import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from memingo.__main__ import analyze_sources


class AnalyzeCommandTests(unittest.TestCase):
    def test_analyze_command_accepts_valid_program(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "main.mgo"
            source.write_text("vibe answer = 40 + 2\nspill answer", encoding="utf-8")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = analyze_sources([str(source)])
            self.assertEqual(code, 0)
            self.assertIn("typed HIR generated", output.getvalue())

    def test_analyze_command_reports_semantic_errors(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "main.mgo"
            source.write_text("spill unknown_name", encoding="utf-8")
            errors = io.StringIO()
            with contextlib.redirect_stderr(errors):
                code = analyze_sources([str(source)])
            self.assertEqual(code, 1)
            self.assertIn("unknown variable 'unknown_name'", errors.getvalue())

    def test_analyze_command_reports_missing_inputs(self):
        errors = io.StringIO()
        with contextlib.redirect_stderr(errors):
            code = analyze_sources(["/path/that/does/not/exist.mgo"])
        self.assertEqual(code, 1)
        self.assertIn("File not found", errors.getvalue())


if __name__ == "__main__":
    unittest.main()
