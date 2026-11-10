import unittest

from memingo.diagnostics import render_diagnostic
from memingo.interpreter import RuntimeErrorMemingo, execute
from memingo.lexer import Lexer, LexerError
from memingo.parser import ParseError, parse


class SmartDiagnosticsTests(unittest.TestCase):
    def test_runtime_error_shows_statement_location(self):
        source = 'vibe answer = 42\\nspill missing_value'
        with self.assertRaises(RuntimeErrorMemingo) as context:
            execute(source)

        output = render_diagnostic(context.exception, source, "main.mgo")
        self.assertIn("main.mgo:2:1", output)
        self.assertIn("spill missing_value", output)
        self.assertIn("^", output)
        self.assertIn("declare it first", output)

    def test_parser_error_shows_token_location(self):
        source = "vibe = 3"
        with self.assertRaises(ParseError) as context:
            parse(source)

        output = render_diagnostic(context.exception, source, "syntax.mgo")
        self.assertIn("syntax.mgo:1:6", output)
        self.assertIn("vibe = 3", output)
        self.assertIn("^", output)

    def test_lexer_error_shows_invalid_character(self):
        source = "spill @"
        with self.assertRaises(LexerError) as context:
            Lexer(source).tokenize()

        output = render_diagnostic(context.exception, source, "lexer.mgo")
        self.assertIn("lexer.mgo:1:7", output)
        self.assertIn("spill @", output)
        self.assertIn("^", output)


if __name__ == "__main__":
    unittest.main()
