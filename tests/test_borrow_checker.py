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
