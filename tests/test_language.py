import unittest

from memingo.interpreter import RuntimeErrorMemingo, execute
from memingo.parser import ParseError


class MemingoLanguageTests(unittest.TestCase):
    def test_variables_and_output(self):
        output = execute('vibe name = "Memingo"\nspill "Hola " + name')
        self.assertEqual(output, ["Hola Memingo"])

    def test_condition(self):
        output = execute('when 8 > 3 { spill "based" } nah { spill "cringe" }')
        self.assertEqual(output, ["based"])

    def test_while_loop_and_assignment(self):
        output = execute('vibe i = 0\ngrind i < 3 { spill i\ni = i + 1 }')
        self.assertEqual(output, ["0", "1", "2"])

    def test_function_and_recursion(self):
        output = execute('ritual factorial(n) { when n <= 1 { drop 1 } drop n * factorial(n - 1) }\nspill factorial(5)')
        self.assertEqual(output, ["120"])

    def test_lists_and_builtin(self):
        output = execute('vibe values = [1, 2, 3]\nspill headcount(values)')
        self.assertEqual(output, ["3"])

    def test_division_by_zero(self):
        with self.assertRaises(RuntimeErrorMemingo):
            execute('spill 10 / 0')

    def test_invalid_syntax(self):
        with self.assertRaises(ParseError):
            execute('vibe = 4')


if __name__ == "__main__":
    unittest.main()
