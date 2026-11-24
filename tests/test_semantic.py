import unittest

from memingo.parser import parse
from memingo.semantic import analyze


class SemanticAnalysisTests(unittest.TestCase):
    def test_valid_program_has_no_diagnostics(self):
        program = parse(
            "ritual double(n) { drop n * 2 }\n"
            "spill double(4)\n"
        )
        self.assertEqual(analyze(program), [])

    def test_duplicate_parameters_are_reported(self):
        program = parse("ritual broken(value, value) { drop value }\n")
        diagnostics = analyze(program)
        self.assertEqual(len(diagnostics), 1)
        self.assertEqual(diagnostics[0].code, "MGO201")
        self.assertIn("Duplicate parameter 'value'", diagnostics[0].message)

    def test_known_function_arity_is_checked(self):
        program = parse(
            "ritual greet(name) { spill name }\n"
            "greet()\n"
        )
        diagnostics = analyze(program)
        self.assertEqual(len(diagnostics), 1)
        self.assertEqual(diagnostics[0].code, "MGO202")
        self.assertIn("expects 1 argument(s), got 0", diagnostics[0].message)

    def test_nested_function_call_uses_visible_scope(self):
        program = parse(
            "ritual outer(value) {\n"
            "  ritual inner() { drop value }\n"
            "  when based {\n"
            "    inner()\n"
            "  }\n"
            "}\n"
        )
        self.assertEqual(analyze(program), [])

    def test_unknown_dynamic_call_is_not_guessed(self):
        program = parse('borrow "community-package"\ncommunity_function(1, 2)\n')
        self.assertEqual(analyze(program), [])


if __name__ == "__main__":
    unittest.main()
