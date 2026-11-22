import unittest

from memingo.compiler import Diagnostic, DiagnosticBag, Label, Severity, SourceFile, SourceMap


class DiagnosticTests(unittest.TestCase):
    def test_renders_source_location_and_caret(self):
        source = SourceFile("main.mgo", 'vibe name = "Memingo"\nspill name')
        sources = SourceMap([source])
        diagnostic = Diagnostic(
            code="M0001",
            message="unknown variable",
            labels=(Label(source.span(5, 9), "not declared", primary=True),),
        )
        rendered = diagnostic.render(sources)
        self.assertIn("error[M0001]: unknown variable", rendered)
        self.assertIn("--> main.mgo:1:6", rendered)
        self.assertIn("^^^^ not declared", rendered)

    def test_bag_tracks_errors_and_warnings(self):
        bag = DiagnosticBag()
        bag.warning("M0002", "unused vibe")
        self.assertFalse(bag.has_errors)
        bag.error("M0003", "unknown name")
        self.assertTrue(bag.has_errors)
        self.assertEqual(len(bag), 2)
        self.assertEqual(len(bag.items), 2)
        bag.clear()
        self.assertEqual(len(bag), 0)

    def test_diagnostic_requires_code_and_message(self):
        with self.assertRaises(ValueError):
            Diagnostic("", "message")
        with self.assertRaises(ValueError):
            Diagnostic("M0004", "")

    def test_severity_is_stable_string_value(self):
        self.assertEqual(Severity.WARNING.value, "warning")


if __name__ == "__main__":
    unittest.main()
