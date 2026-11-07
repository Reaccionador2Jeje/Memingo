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

    def test_objects_lists_and_json(self):
        output = execute('vibe user = {name: "Ana", role: "dev"}\nvibe users = [user]\nspill user.name\nspill json_stringify(users)')
        self.assertEqual(output, ['Ana', '[{"name":"Ana","role":"dev"}]'])

    def test_mutable_collections(self):
        output = execute('vibe values = []\npush(values, "based")\nset_value(values, 0, "cringe")\nspill values[0]')
        self.assertEqual(output, ["cringe"])

    def test_json_round_trip(self):
        output = execute('vibe value = json_parse("{\\\"meme\\\":\\\"based\\\"}")\nspill value["meme"]')
        self.assertEqual(output, ["based"])


if __name__ == "__main__":
    unittest.main()
