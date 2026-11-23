import unittest

from memingo.diagnostics import format_diagnostic


class DiagnosticRenderingTests(unittest.TestCase):
    def test_renders_location_and_context(self):
        source = 'vibe name = "Memingo"\nspill missing\nspill "after"\n'
        rendered = format_diagnostic(
            RuntimeError("Undefined variable 'missing' at line 2, column 7"),
            source,
            "main.mgo",
        )
        self.assertIn("main.mgo:2:7", rendered)
        self.assertIn("2 | spill missing", rendered)
        self.assertIn("^", rendered)
        self.assertIn("Undefined variable 'missing'", rendered)

    def test_renders_first_and_last_line_without_out_of_range_context(self):
        first = format_diagnostic(ValueError("Unexpected token at line 1, column 1"), "bad\n", "bad.mgo")
        last = format_diagnostic(ValueError("Unexpected token at line 2, column 4"), "ok\nbad", "bad.mgo")
        self.assertIn("bad.mgo:1:1", first)
        self.assertIn("bad.mgo:2:4", last)

    def test_falls_back_for_errors_without_location(self):
        rendered = format_diagnostic(ValueError("something failed"), "", "main.mgo")
        self.assertEqual(rendered, "error in main.mgo: something failed")


if __name__ == "__main__":
    unittest.main()
