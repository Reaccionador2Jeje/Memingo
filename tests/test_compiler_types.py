import unittest

from memingo.compiler import (
    BASED, CAPTION, DECIMAL, GHOST, WHOLE, check, common_type,
    is_assignable, list_of,
)
from memingo.parser import parse


class TypeModelTests(unittest.TestCase):
    def test_numeric_widening(self):
        self.assertEqual(common_type(WHOLE, DECIMAL), DECIMAL)
        self.assertTrue(is_assignable(DECIMAL, WHOLE))
        self.assertFalse(is_assignable(WHOLE, DECIMAL))

    def test_collection_types(self):
        self.assertEqual(str(list_of(WHOLE)), "party[whole]")
        self.assertEqual(common_type(list_of(WHOLE), list_of(DECIMAL)), list_of(DECIMAL))


class TypeCheckerTests(unittest.TestCase):
    def test_infers_basic_types_and_collections(self):
        result = check(parse('''
vibe count = 42
vibe ratio = 4.5
vibe title = "Memingo"
vibe enabled = based
vibe nothing = ghost
vibe numbers = [1, 2, 3]
'''))
        self.assertFalse(result.has_errors)
        self.assertIn(list_of(WHOLE), result.expression_types.values())
        self.assertIn(CAPTION, result.expression_types.values())
        self.assertIn(BASED, result.expression_types.values())
        self.assertIn(GHOST, result.expression_types.values())
        self.assertIn(DECIMAL, result.expression_types.values())

    def test_unknown_variable_is_reported(self):
        result = check(parse("spill missing"))
        self.assertTrue(result.has_errors)
        self.assertEqual(result.diagnostics[0].code, "M1002")
        self.assertIn("unknown variable 'missing'", result.diagnostics[0].message)

    def test_assignment_type_mismatch_is_reported(self):
        result = check(parse('vibe score = 10\nscore = "ten"'))
        self.assertTrue(any(item.code == "M1003" for item in result.diagnostics))

    def test_if_and_loop_require_boolean_conditions(self):
        result = check(parse('''
when 123 { spill "no" }
grind "forever" { spill "no" }
'''))
        self.assertEqual(sum(item.code == "M1004" for item in result.diagnostics), 2)

    def test_arithmetic_and_comparison_types(self):
        result = check(parse('''
vibe total = 2 + 3
vibe ratio = total / 2
vibe valid = total >= 5
'''))
        self.assertFalse(result.has_errors)
        self.assertIn(DECIMAL, result.expression_types.values())
        self.assertIn(BASED, result.expression_types.values())

    def test_function_parameters_and_call_arity(self):
        result = check(parse('''
ritual greet(name) { spill name }
greet("Memingo")
greet()
'''))
        self.assertTrue(any(item.code == "M1009" for item in result.diagnostics))

    def test_function_return_type_is_inferred_from_guaranteed_return(self):
        result = check(parse(
            'ritual answer() { drop 42 }\n'
            'vibe result = answer()\n'
            'result = "wrong"'
        ))
        self.assertTrue(any(item.code == "M1003" for item in result.diagnostics))

    def test_both_if_branches_can_infer_a_function_return_type(self):
        result = check(parse(
            'ritual choose(flag) { when flag { drop 1 } nah { drop 2 } }\n'
            'vibe result = choose(based)\n'
            'result = "wrong"'
        ))
        self.assertTrue(any(item.code == "M1003" for item in result.diagnostics))

    def test_function_with_possible_fallthrough_keeps_dynamic_return_type(self):
        result = check(parse(
            'ritual maybe(flag) { when flag { drop 1 } }\n'
            'vibe result = maybe(based)\n'
            'result = "still dynamic"'
        ))
        self.assertFalse(any(item.code == "M1003" for item in result.diagnostics))

    def test_function_without_return_infers_ghost(self):
        result = check(parse(
            'ritual announce() { spill "hello" }\n'
            'vibe result = announce()\n'
            'result = 1'
        ))
        self.assertTrue(any(item.code == "M1003" for item in result.diagnostics))

    def test_scopes_do_not_leak_from_blocks(self):
        result = check(parse('''
when based { vibe hidden = 1 }
spill hidden
'''))
        self.assertTrue(any(item.code == "M1002" for item in result.diagnostics))

    def test_spans_are_attached_to_type_errors(self):
        result = check(parse('vibe count = 1\ncount = "bad"', source_id="main.mgo"))
        error = next(item for item in result.diagnostics if item.code == "M1003")
        self.assertEqual(error.labels[0].span.source_id, "main.mgo")


if __name__ == "__main__":
    unittest.main()
