import unittest

from memingo.compiler import compile_source


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
            '  vibe escaped = view\\n'
            '}'
        )
        self.assertTrue(any(item.code == "M2204" for item in result.diagnostics))

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
