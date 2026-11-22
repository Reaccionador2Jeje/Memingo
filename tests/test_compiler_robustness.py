import unittest

from memingo.compiler import ANY, Type, TypeKind, TypeChecker, check, compile_source
from memingo.parser import parse


class CompilerRobustnessTests(unittest.TestCase):
    def test_type_constructors_validate_shape(self):
        with self.assertRaises(ValueError):
            Type(TypeKind.LIST)
        with self.assertRaises(ValueError):
            Type(TypeKind.FUNCTION)
        self.assertEqual(Type(TypeKind.ANY), ANY)

    def test_structurally_equal_any_types_are_dynamic(self):
        dynamic = Type(TypeKind.ANY)
        self.assertTrue(__import__("memingo.compiler", fromlist=["is_assignable"]).is_assignable(dynamic, ANY))

    def test_checker_can_be_reused_without_leaking_symbols_or_errors(self):
        checker = TypeChecker()
        first = checker.check(parse("spill missing"))
        self.assertTrue(first.has_errors)
        second = checker.check(parse("vibe valid = based"))
        self.assertFalse(second.has_errors)
        self.assertEqual(len(second.diagnostics), 0)

    def test_duplicate_function_names_are_reported(self):
        result = check(parse('''
ritual same() { drop ghost }
ritual same() { drop ghost }
'''))
        self.assertTrue(any(item.code == "M1001" for item in result.diagnostics))

    def test_duplicate_function_parameters_are_reported(self):
        result = check(parse("ritual repeat(value, value) { spill value }"))
        self.assertTrue(any(item.code == "M1014" for item in result.diagnostics))

    def test_compiler_public_api_is_importable(self):
        result = compile_source("spill 42")
        self.assertTrue(result.succeeded)


if __name__ == "__main__":
    unittest.main()
