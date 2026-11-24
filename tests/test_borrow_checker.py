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
            'vibe items = [1, 2]\\n'
            'borrow items as view {\\n'
            '  spill headcount(view)\\n'
            '}'
        )
        self.assertFalse(any(item.code.startswith("M22") for item in result.diagnostics))

    def test_immutable_reference_rejects_mutation(self):
        result = compile_source(
            'vibe items = [1, 2]\\n'
            'borrow items as view {\\n'
            '  push(view, 3)\\n'
            '}'
        )
        self.assertTrue(any(item.code == "M2202" for item in result.diagnostics))

    def test_mutable_reference_rejects_source_access(self):
        result = compile_source(
            'vibe items = [1, 2]\\n'
            'borrow mut items as edit {\\n'
            '  spill headcount(items)\\n'
            '}'
        )
        self.assertTrue(any(item.code == "M2203" for item in result.diagnostics))

    def test_mutable_reference_allows_mutation_through_alias(self):
        result = compile_source(
            'vibe items = [1, 2]\\n'
            'borrow mut items as edit {\\n'
            '  push(edit, 3)\\n'
            '}'
        )
        self.assertFalse(any(item.code.startswith("M22") for item in result.diagnostics))

    def test_reference_cannot_escape_its_scope(self):
        result = compile_source(
            'vibe items = [1, 2]\\n'
            'borrow items as view {\\n'
            '  items = view\\n'
            '}'
        )
        self.assertTrue(any(item.code == "M2204" for item in result.diagnostics))

    def test_runtime_executes_immutable_reference_scope(self):
        interpreter = Interpreter()
        interpreter.run(parse(
            'vibe items = [1, 2]\\n'
            'borrow items as view {\\n'
            '  spill headcount(view)\\n'
            '}'
        ))
        self.assertEqual(interpreter.output, ["2"])

    def test_runtime_executes_mutable_reference_scope(self):
        interpreter = Interpreter()
        interpreter.run(parse(
            'vibe items = [1, 2]\\n'
            'borrow mut items as edit {\\n'
            '  push(edit, 3)\\n'
            '}\\n'
            'spill headcount(items)'
        ))
        self.assertEqual(interpreter.output, ["3"])

    def test_immutable_reference_rejects_mutating_original_source(self):
        result = compile_source(
            'vibe items = [1, 2]\\n'
            'borrow items as view {\\n'
            '  push(items, 3)\\n'
            '}'
        )
        self.assertTrue(any(item.code == "M2202" for item in result.diagnostics))

    def test_nested_overlapping_mutable_borrows_are_rejected(self):
        result = compile_source(
            'vibe items = [1, 2]\\n'
            'borrow items as first {\\n'
            '  borrow mut items as second {\\n'
            '    push(second, 3)\\n'
            '  }\\n'
            '}'
        )
        self.assertTrue(any(item.code == "M2205" for item in result.diagnostics))

    def test_runtime_rejects_mutation_through_immutable_reference(self):
        interpreter = Interpreter()
        with self.assertRaisesRegex(Exception, "immutable reference"):
            interpreter.run(parse(
                'vibe items = [1, 2]\\n'
                'borrow items as view {\\n'
                '  push(view, 3)\\n'
                '}'
            ))

    def test_runtime_rejects_source_access_during_mutable_reference(self):
        interpreter = Interpreter()
        with self.assertRaisesRegex(Exception, "borrowed source"):
            interpreter.run(parse(
                'vibe items = [1, 2]\\n'
                'borrow mut items as edit {\\n'
                '  spill headcount(items)\\n'
                '}'
            ))

    def test_runtime_rejects_reassigning_borrowed_source(self):
        interpreter = Interpreter()
        with self.assertRaisesRegex(Exception, "borrowed source"):
            interpreter.run(parse(
                'vibe items = [1, 2]\\n'
                'borrow items as view {\\n'
                '  items = [3]\\n'
                '}'
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
