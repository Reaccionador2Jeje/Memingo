import unittest

from memingo.compiler import compile_source
from memingo.interpreter import Interpreter
from memingo.parser import parse


class BorrowCheckerTests(unittest.TestCase):
    def test_mutating_builtin_rejects_same_collection_as_value(self):
        result = compile_source(
            'vibe items = [1, 2]\n'
            'push(items, items)'
        )
        self.assertFalse(result.succeeded)
        self.assertTrue(any(item.code == "M2101" for item in result.diagnostics))

    def test_mutating_builtin_rejects_nested_alias(self):
        result = compile_source(
            'vibe profile = {name: "Cris"}\n'
            'set_value(profile, "backup", profile.name)'
        )
        self.assertFalse(result.succeeded)
        self.assertTrue(any(item.code == "M2101" for item in result.diagnostics))

    def test_immutable_reference_scope_is_allowed_for_reads(self):
        result = compile_source(
            'vibe items = [1, 2]\n'
            'borrow items as view {\n'
            '  spill headcount(view)\n'
            '}'
        )
        self.assertTrue(result.succeeded, result.diagnostics)

    def test_immutable_reference_rejects_mutation(self):
        result = compile_source(
            'vibe items = [1, 2]\n'
            'borrow items as view {\n'
            '  push(view, 3)\n'
            '}'
        )
        self.assertTrue(any(item.code == "M2202" for item in result.diagnostics))

    def test_mutable_reference_rejects_source_access(self):
        result = compile_source(
            'vibe items = [1, 2]\n'
            'borrow mut items as edit {\n'
            '  spill headcount(items)\n'
            '}'
        )
        self.assertTrue(any(item.code == "M2203" for item in result.diagnostics))

    def test_mutable_reference_allows_mutation_through_alias(self):
        result = compile_source(
            'vibe items = [1, 2]\n'
            'borrow mut items as edit {\n'
            '  push(edit, 3)\n'
            '}'
        )
        self.assertTrue(result.succeeded, result.diagnostics)

    def test_reference_cannot_escape_its_scope(self):
        result = compile_source(
            'vibe items = [1, 2]\n'
            'borrow items as view {\n'
            '  items = view\n'
            '}'
        )
        self.assertTrue(any(item.code == "M2204" for item in result.diagnostics))

    def test_immutable_reference_rejects_source_rebinding(self):
        result = compile_source(
            'vibe items = [1, 2]\n'
            'borrow items as view {\n'
            '  items = [3]\n'
            '}'
        )
        self.assertTrue(any(item.code == "M2202" for item in result.diagnostics))

    def test_nested_mutable_borrow_through_alias_is_rejected(self):
        result = compile_source(
            'vibe items = [1, 2]\n'
            'borrow items as view {\n'
            '  borrow mut view as edit {\n'
            '    push(edit, 3)\n'
            '  }\n'
            '}'
        )
        self.assertTrue(any(item.code == "M2205" for item in result.diagnostics))

    def test_runtime_executes_immutable_reference_scope(self):
        interpreter = Interpreter()
        interpreter.run(parse(
            'vibe items = [1, 2]\n'
            'borrow items as view {\n'
            '  spill headcount(view)\n'
            '}'
        ))
        self.assertEqual(interpreter.output, ["2"])

    def test_runtime_executes_mutable_reference_scope(self):
        interpreter = Interpreter()
        interpreter.run(parse(
            'vibe items = [1, 2]\n'
            'borrow mut items as edit {\n'
            '  push(edit, 3)\n'
            '}\n'
            'spill headcount(items)'
        ))
        self.assertEqual(interpreter.output, ["3"])

    def test_immutable_reference_rejects_mutating_original_source(self):
        result = compile_source(
            'vibe items = [1, 2]\n'
            'borrow items as view {\n'
            '  push(items, 3)\n'
            '}'
        )
        self.assertTrue(any(item.code == "M2202" for item in result.diagnostics))

    def test_nested_overlapping_mutable_borrows_are_rejected(self):
        result = compile_source(
            'vibe items = [1, 2]\n'
            'borrow items as first {\n'
            '  borrow mut items as second {\n'
            '    push(second, 3)\n'
            '  }\n'
            '}'
        )
        self.assertTrue(any(item.code == "M2205" for item in result.diagnostics))

    def test_runtime_rejects_mutation_through_immutable_reference(self):
        interpreter = Interpreter()
        with self.assertRaisesRegex(Exception, "immutable reference"):
            interpreter.run(parse(
                'vibe items = [1, 2]\n'
                'borrow items as view {\n'
                '  push(view, 3)\n'
                '}'
            ))

    def test_runtime_rejects_source_access_during_mutable_reference(self):
        interpreter = Interpreter()
        with self.assertRaisesRegex(Exception, "borrowed source"):
            interpreter.run(parse(
                'vibe items = [1, 2]\n'
                'borrow mut items as edit {\n'
                '  spill headcount(items)\n'
                '}'
            ))

    def test_runtime_rejects_reassigning_borrowed_source(self):
        interpreter = Interpreter()
        with self.assertRaisesRegex(Exception, "borrowed source"):
            interpreter.run(parse(
                'vibe items = [1, 2]\n'
                'borrow items as view {\n'
                '  items = [3]\n'
                '}'
            ))

    def test_ritual_accepts_immutable_borrowed_parameter(self):
        source = (
            'ritual inspect(borrow items) {\n'
            '  spill headcount(items)\n'
            '}\n'
            'vibe values = [1, 2]\n'
            'inspect(values)'
        )
        result = compile_source(source)
        self.assertTrue(result.succeeded, result.diagnostics)
        interpreter = Interpreter()
        interpreter.run(parse(source))
        self.assertEqual(interpreter.output, ["2"])

    def test_ritual_accepts_mutable_borrowed_parameter(self):
        source = (
            'ritual append_item(borrow mut items) {\n'
            '  push(items, 3)\n'
            '}\n'
            'vibe values = [1, 2]\n'
            'append_item(values)\n'
            'spill headcount(values)'
        )
        result = compile_source(source)
        self.assertTrue(result.succeeded, result.diagnostics)
        interpreter = Interpreter()
        interpreter.run(parse(source))
        self.assertEqual(interpreter.output, ["3"])

    def test_immutable_borrowed_parameter_rejects_mutation(self):
        result = compile_source(
            'ritual inspect(borrow items) {\n'
            '  push(items, 3)\n'
            '}'
        )
        self.assertTrue(any(item.code == "M2202" for item in result.diagnostics))

    def test_borrowed_parameter_requires_variable_argument(self):
        result = compile_source(
            'ritual inspect(borrow items) {\n'
            '  spill headcount(items)\n'
            '}\n'
            'inspect([1, 2])'
        )
        self.assertTrue(any(item.code == "M2206" for item in result.diagnostics))

    def test_overlapping_borrowed_ritual_arguments_are_rejected(self):
        result = compile_source(
            'ritual compare(borrow mut first, borrow second) {\n'
            '  spill headcount(first)\n'
            '}\n'
            'vibe values = [1, 2]\n'
            'compare(values, values)'
        )
        self.assertTrue(any(item.code == "M2205" for item in result.diagnostics))

    def test_borrowed_parameter_cannot_escape_through_assignment(self):
        result = compile_source(
            'ritual leak(borrow items) {\n'
            '  vibe saved = items\n'
            '  drop saved\n'
            '}'
        )
        self.assertTrue(any(item.code == "M2204" for item in result.diagnostics))

    def test_borrowed_parameter_cannot_be_reassigned(self):
        result = compile_source(
            'ritual replace(borrow items) {\n'
            '  items = [9]\n'
            '}'
        )
        self.assertTrue(any(item.code == "M2207" for item in result.diagnostics))

    def test_runtime_rejects_mutation_through_immutable_borrowed_parameter(self):
        interpreter = Interpreter()
        with self.assertRaisesRegex(Exception, "immutable reference"):
            interpreter.run(parse(
                'ritual modify(borrow items) {\n'
                '  push(items, 3)\n'
                '}\n'
                'vibe values = [1, 2]\n'
                'modify(values)'
            ))

    def test_mutation_without_alias_is_allowed(self):
        result = compile_source(
            'vibe items = [1, 2]\n'
            'push(items, 3)'
        )
        self.assertFalse(any(item.code == "M2101" for item in result.diagnostics))

    def test_non_mutating_calls_are_not_rejected(self):
        result = compile_source(
            'vibe items = [1, 2]\n'
            'spill headcount(items)'
        )
        self.assertFalse(any(item.code == "M2101" for item in result.diagnostics))


if __name__ == "__main__":
    unittest.main()
