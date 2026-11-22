import unittest

from memingo.compiler import Span
from memingo.lexer import Lexer
from memingo.parser import Binary, Let, Say, parse


class FrontendSpanTests(unittest.TestCase):
    def test_lexer_records_half_open_token_offsets(self):
        source = 'vibe answer = 42\nspill "based"'
        tokens = Lexer(source).tokenize()

        self.assertEqual((tokens[0].kind, tokens[0].start_offset, tokens[0].end_offset),
                         ("VIBE", 0, 4))
        number = next(token for token in tokens if token.kind == "NUMBER")
        self.assertEqual(source[number.start_offset:number.end_offset], "42")
        string = next(token for token in tokens if token.kind == "STRING")
        self.assertEqual(source[string.start_offset:string.end_offset], '"based"')
        self.assertEqual(tokens[-1].kind, "EOF")
        self.assertEqual(tokens[-1].start_offset, len(source))
        self.assertEqual(tokens[-1].end_offset, len(source))

    def test_parser_attaches_source_spans_to_statements_and_expressions(self):
        source = "vibe answer = 6 * 7\nspill answer"
        program = parse(source, source_id="example.mgo")

        declaration = program.statements[0]
        self.assertIsInstance(declaration, Let)
        self.assertEqual(declaration.span, Span("example.mgo", 0, 19))
        self.assertIsInstance(declaration.value, Binary)
        self.assertEqual(declaration.value.span, Span("example.mgo", 14, 19))

        output = program.statements[1]
        self.assertIsInstance(output, Say)
        self.assertEqual(output.span, Span("example.mgo", 20, len(source)))
        self.assertEqual(output.value.span, Span("example.mgo", 26, len(source)))

    def test_parse_keeps_default_source_identity(self):
        program = parse("spill 1")
        self.assertEqual(program.statements[0].span.source_id, "<memory>")


if __name__ == "__main__":
    unittest.main()
