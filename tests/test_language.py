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

    def test_multiline_lists_and_objects(self):
        source = (
            'vibe world = {\n  name: "MemeCraft",\n  day: based,\n  size: 30\n}\n'
            'vibe materials = [\n  {name: "grass", solid: based},\n  {name: "stone", solid: cringe},\n]\n'
            'spill world.name\n'
            'spill headcount(materials)\n'
            'spill materials[1].name'
        )
        self.assertEqual(execute(source), ["MemeCraft", "2", "stone"])

    def test_multiline_parameters(self):
        source = (
            'ritual add(\n  a,\n  b,\n) {\n  drop a + b\n}\n'
            'spill add(\n  1,\n  2,\n)'
        )
        self.assertEqual(execute(source), ["3"])

    def test_builtin_errors_are_wrapped(self):
        with self.assertRaises(RuntimeErrorMemingo) as context:
            execute("spill headcount(1)")
        self.assertIn("headcount", str(context.exception))

    def test_whatkind_and_borrow_validation(self):
        output = execute('spill whatkind(based)\nspill whatkind(1)\nspill whatkind("x")\nspill whatkind(ghost)')
        self.assertEqual(output, ["based-or-cringe", "whole", "caption", "ghost"])
        with self.assertRaises(RuntimeErrorMemingo):
            execute('borrow "../escape"')

    def test_json_round_trip(self):
        output = execute('vibe value = json_parse("{\\\"meme\\\":\\\"based\\\"}")\nspill value["meme"]')
        self.assertEqual(output, ["based"])

    def test_string_builtins(self):
        source = (
            'vibe text = "  Memingo Rocks  "\n'
            'spill trim(text)\n'
            'spill upper("meme")\n'
            'spill lower("MEME")\n'
            'spill replace("meme life", "meme", "based")\n'
            'spill join(split("a,b,c", ","), "-")\n'
            'spill contains("memingo", "ming")\n'
            'spill starts_with("memingo", "mem")\n'
            'spill ends_with("memingo", "go")\n'
            'spill slice([1, 2, 3, 4], 1, 3)'
        )
        self.assertEqual(
            execute(source),
            ["Memingo Rocks", "MEME", "meme", "based life", "a-b-c", "based", "based", "based", "[2, 3]"],
        )

    def test_collection_builtins(self):
        source = (
            'vibe values = [3, 1, 2]\n'
            'spill sort(values)\n'
            'spill reverse(values)\n'
            'spill sum(values)\n'
            'spill min(values)\n'
            'spill max(values)\n'
            'spill values'
        )
        self.assertEqual(
            execute(source),
            ["[1, 2, 3]", "[2, 1, 3]", "6", "1", "3", "[3, 1, 2]"],
        )

    def test_higher_order_builtins(self):
        source = (
            'ritual double(n) { drop n * 2 }\n'
            'ritual even(n) { drop n % 2 == 0 }\n'
            'ritual combine(a, b) { drop a + b }\n'
            'spill map([1, 2, 3], double)\n'
            'spill filter([1, 2, 3, 4], even)\n'
            'spill reduce([1, 2, 3, 4], combine, 0)'
        )
        self.assertEqual(execute(source), ["[2, 4, 6]", "[2, 4]", "10"])

    def test_math_and_range_builtins(self):
        source = (
            'spill abs(-7)\n'
            'spill floor(2.9)\n'
            'spill ceil(2.1)\n'
            'spill round(2.6)\n'
            'spill clamp(12, 0, 10)\n'
            'spill parse_int("42")\n'
            'spill parse_float("2.5")\n'
            'spill range(2, 8, 2)\n'
            'spill values({a: 1, b: 2})'
        )
        self.assertEqual(execute(source), ["7", "2", "3", "3", "10", "42", "2.5", "[2, 4, 6]", "[1, 2]"])

    def test_new_builtin_argument_validation(self):
        with self.assertRaises(RuntimeErrorMemingo) as context:
            execute('spill upper(3)')
        self.assertIn("upper", str(context.exception))
        with self.assertRaises(RuntimeErrorMemingo):
            execute('spill map("nope", upper)')
        with self.assertRaises(RuntimeErrorMemingo):
            execute('spill reduce([], upper)')
        with self.assertRaises(RuntimeErrorMemingo):
            execute('spill parse_int("not-a-number")')


if __name__ == "__main__":
    unittest.main()
