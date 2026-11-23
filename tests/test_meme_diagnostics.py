import unittest

from memingo.diagnostics import classify_error, format_diagnostic
from memingo.interpreter import Interpreter, RuntimeErrorMemingo
from memingo.parser import parse
from memingo.lexer import LexerError
from memingo.parser import ParseError


class MemeDiagnosticTests(unittest.TestCase):
    def test_classifies_syntax_and_runtime_errors(self):
        self.assertEqual(classify_error(ParseError("unexpected token")), "BRUH")
        self.assertEqual(classify_error(LexerError("bad character")), "BRUH")
        self.assertEqual(classify_error(RuntimeErrorMemingo("Undefined variable 'player'")), "SKILL_ISSUE")
        self.assertEqual(classify_error(RuntimeErrorMemingo("Division by zero")), "RATIO")
        self.assertEqual(classify_error(RuntimeErrorMemingo("Cannot access key")), "GHOSTED")
        self.assertEqual(classify_error(RuntimeErrorMemingo("Debug trace limit reached")), "OVERCOOKED")
        self.assertEqual(classify_error(RuntimeErrorMemingo("Something else")), "SUS")

    def test_meme_diagnostic_shows_location_and_source_caret(self):
        error = ParseError("Expected ')' after expression at line 2, column 7")
        rendered = format_diagnostic(error, 'spill "ok"\nspill (2 +', "main.mgo")
        self.assertIn("BRUH", rendered)
        self.assertIn("main.mgo:2:7", rendered)
        self.assertIn("^", rendered)

    def test_undefined_name_suggests_close_identifier(self):
        error = RuntimeErrorMemingo("Undefined variable 'plaeyr'")
        rendered = format_diagnostic(error, "vibe player = 1\nspill plaeyr")
        self.assertIn("Did you mean 'player'?", rendered)

    def test_runtime_errors_receive_statement_source_location(self):
        interpreter = Interpreter()
        with self.assertRaises(RuntimeErrorMemingo) as context:
            interpreter.run(parse('vibe player = 1\nspill plaeyr'))
        self.assertIn("line 2, column 1", str(context.exception))
        rendered = format_diagnostic(context.exception, 'vibe player = 1\nspill plaeyr', "main.mgo")
        self.assertIn("main.mgo:2:1", rendered)
        self.assertIn("Did you mean 'player'?", rendered)

    def test_serious_mode_is_plain_and_machine_friendly(self):
        error = ParseError("Unexpected token at line 1, column 3")
        rendered = format_diagnostic(error, "xx", "main.mgo", "serious")
        self.assertEqual(rendered, "main.mgo:1:3: error: Unexpected token at line 1, column 3")


if __name__ == "__main__":
    unittest.main()
